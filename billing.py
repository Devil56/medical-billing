from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flashing messages

class Medicine:
    def __init__(self, name, price, quantity):
        self.name = name
        self.price = price
        self.quantity = quantity

class BillingSystem:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["medical_store"]
        self.medicines_collection = self.db["medicines"]
        self.purchases_collection = self.db["purchases"]
        self.add_initial_medicines()

    def add_initial_medicines(self):
        initial_medicines = [
            Medicine("Paracetamol", 50, 100),
            Medicine("Aspirin", 70, 50),
            Medicine("Antibiotics", 250, 30)
        ]
        for medicine in initial_medicines:
            self.add_medicine(medicine)

    def add_medicine(self, medicine):
        if not self.medicines_collection.find_one({"name": medicine.name}):
            self.medicines_collection.insert_one({
                "name": medicine.name,
                "price": medicine.price,
                "quantity": medicine.quantity
            })
            print(f"Added medicine: {medicine.name}, Price: {medicine.price}, Quantity: {medicine.quantity}")
        else:
            print(f"Medicine {medicine.name} already exists in the database.")

    def update_medicine_quantity(self, name, new_quantity):
        medicine = self.medicines_collection.find_one({"name": name})
        if medicine:
            self.medicines_collection.update_one({"name": name}, {"$set": {"quantity": new_quantity}})
            print(f"Updated {name} quantity to {new_quantity}.")
        else:
            print(f"{name} not found in stock")

    def buy_medicine(self, name, quantity, signature):
        medicine = self.medicines_collection.find_one({"name": name})
        if medicine:
            if medicine["quantity"] >= quantity:
                new_quantity = medicine["quantity"] - quantity
                total_price = quantity * medicine["price"]
                profit = total_price  # Assuming profit is the total price in this case
                date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.medicines_collection.update_one({"name": name}, {"$set": {"quantity": new_quantity}})
                transaction_id = self.purchases_collection.insert_one({
                    "name": name,
                    "price": medicine["price"],
                    "quantity": quantity,
                    "total_price": total_price,
                    "profit": profit,
                    "date": date,
                    "signature": signature
                }).inserted_id
                transaction = self.purchases_collection.find_one({"_id": transaction_id})
                self.generate_receipt(transaction)
                return True, f"Transaction successful! Purchased {quantity} units of {name}."
            else:
                return False, f"Insufficient stock of {name}. Available quantity: {medicine['quantity']}"
        else:
            return False, f"{name} not found in stock"

    def generate_receipt(self, transaction):
        receipt_content = (
            f"Receipt\n"
            f"-----------------------------------\n"
            f"Medicine Name: {transaction['name']}\n"
            f"Quantity: {transaction['quantity']}\n"
            f"Price per unit: Rs.{transaction['price']}\n"
            f"Total Price: Rs.{transaction['total_price']}\n"
            f"Date: {transaction['date']}\n"
            f"Signature: {transaction['signature']}\n"
            f"-----------------------------------\n"
            f"Thank you for your purchase!"
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        receipt_filename = f"receipt_{transaction['_id']}_{timestamp}.txt"
        with open(receipt_filename, 'w') as file:
            file.write(receipt_content)
        print(f"Receipt has been generated and saved as {receipt_filename}")

billing_system = BillingSystem()

@app.route('/')
def index():
    medicines = list(billing_system.medicines_collection.find())
    return render_template('index.html', medicines=medicines)

@app.route('/buy', methods=['POST'])
def buy():
    name = request.form['name']
    quantity = int(request.form['quantity'])
    signature = request.form['signature']
    success, message = billing_system.buy_medicine(name, quantity, signature)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('index'))

@app.route('/update', methods=['POST'])
def update():
    name = request.form['name']
    new_quantity = int(request.form['new_quantity'])
    billing_system.update_medicine_quantity(name, new_quantity)
    flash(f"Updated {name} quantity to {new_quantity}.", 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
