from flask import Flask, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector.errors import IntegrityError
from functools import wraps
from flask import render_template_string


app = Flask(__name__)
app.secret_key = "your_secret_key"
bcrypt = Bcrypt(app)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Kavya@1405",
    database="car_showroom"
)
cursor = db.cursor(dictionary=True)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            return "Access denied! Admins only."
        return f(*args, **kwargs)
    return login_required(decorated)

def customer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "customer":
            return "Access denied! Customers only."
        return f(*args, **kwargs)
    return login_required(decorated)


@app.route("/")
def home():
    return redirect("/login")

@app.route("/register", methods=["GET"])
def show_register():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]
    password = request.form["password"]

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    sql = "INSERT INTO Users (Name, Email, Phone, Password, Role) VALUES (%s, %s, %s, %s, %s)"
    values = (name, email, phone, hashed_password, "customer")

    try:
        cursor.execute(sql, values)
        db.commit()
        return "Registration successful!"
    except IntegrityError:
        return render_template_string('''
            <script>
                alert("Email already registered!");
                window.location.href = "/register";
            </script>
        ''')


@app.route("/login", methods=["GET"])
def show_login():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    cursor.execute("SELECT * FROM Users WHERE Email = %s", (email,))
    user = cursor.fetchone()

    if user and bcrypt.check_password_hash(user["Password"], password):
        session["user_id"] = user["User_ID"]
        session["role"] = user["Role"]

        if user["Role"] == "admin":
            return redirect("/admin")
        else:
            return redirect("/customer/home")
    else:
        return render_template_string('''
        <script>
            alert("Invalid Credentials!");
            window.location.href = "/login";
        </script>
     ''')
    


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")




@app.route("/customer/home")
# @customer_required
def customer_home():
    cursor.execute("SELECT * FROM Cars")
    cars = cursor.fetchall()
    return render_template('customer_home.html', cars=cars)

@app.route("/car/<int:car_id>")
# @customer_required
def view_car(car_id):
    cursor.execute("SELECT * FROM Cars WHERE Car_ID = %s", (car_id,))
    car = cursor.fetchone()
    if not car:
        return "Car not found!"
    return render_template("car_details.html", car=car)

@app.route("/book_test_drive/<int:car_id>")
def book_testdrive(car_id):
    cursor.execute("SELECT * FROM Cars WHERE Car_ID = %s", (car_id,))
    car = cursor.fetchone()
    if not car:
        return "Car not found!"

    showroom_id = car["Showroom_ID"]
    cursor.execute("SELECT * FROM Showrooms WHERE Showroom_ID = %s", (showroom_id,))
    showroom = cursor.fetchone()

    return render_template("book_testdrive.html", car=car, showroom=showroom)

@app.route("/confirm_booking/<int:car_id>", methods=["POST"])
def confirm_booking(car_id):
    date = request.form.get("date")
    time = request.form.get("time")
    user_id = session.get("user_id")  # Assuming the logged-in user's ID is stored in session

    if not user_id:
        return "You must be logged in to book a test drive.", 401

    cursor.execute("""
        INSERT INTO testdrive_bookings (User_ID, Car_ID, Booking_Date, Booking_Time, Status)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, car_id, date, time, 'Pending'))

    db.commit()
    return render_template_string('''
        <script>
            alert("Test Drive Request placed successfully!");
            window.location.href = "/my_activity";
        </script>
    ''')

@app.route("/buy_now/<int:car_id>", methods=["GET"])
@login_required
def buy_now(car_id):
    cursor.execute("SELECT * FROM Cars WHERE Car_ID = %s", (car_id,))
    car = cursor.fetchone()
    if not car:
        return "Car not found!"

    showroom_id = car["Showroom_ID"]
    cursor.execute("SELECT * FROM Showrooms WHERE Showroom_ID = %s", (showroom_id,))
    showroom = cursor.fetchone()

    return render_template("buy_now.html", car=car, showroom=showroom)

@app.route("/buy_now/<int:car_id>", methods=["POST"])
@login_required
def confirm_purchase(car_id):
    payment_mode = request.form.get("payment_mode")
    amount = request.form.get("amount")
    user_id = session.get("user_id")

    if not user_id:
        return "You must be logged in to buy a car.", 401

    cursor.execute("""
        INSERT INTO sales (User_ID, Car_ID, Sale_Date, Payment_Mode, Amount)
        VALUES (%s, %s, CURDATE(), %s, %s)
    """, (user_id, car_id, payment_mode, amount))

    db.commit()
    return render_template_string('''
            <script>
                alert("Car Purchase Successful");
                window.location.href = "/customer/home";
            </script>''')


@app.route("/request_service", methods=["GET"])
@login_required
def request_service():
    cursor.execute("SELECT Car_ID, Brand, Model, Fuel_Type, Transmission FROM Cars")
    cars = cursor.fetchall()  # list of dicts
    
    return render_template("request_service.html", cars=cars)


@app.route("/submit_service_request", methods=["POST"])
@login_required
def submit_service_request():
    car_id = request.form.get("car_id")
    description = request.form.get("description")
    user_id = session["user_id"]

    cursor.execute("""
        INSERT INTO service_requests (User_ID, Car_ID, Request_Date, Description, Status)
        VALUES (%s, %s, CURDATE(), %s, 'Pending')
    """, (user_id, car_id, description))

    db.commit()

    return render_template_string('''
            <script>
                alert("Service request submitted successfully!");
                window.location.href = "/my_activity";
            </script>
        ''')

@app.route("/my_activity", methods=["GET"])
@login_required
def my_activity():
    user_id = session["user_id"]

    cursor.execute("""
        SELECT b.Booking_ID, c.Brand, c.Model, b.Booking_Date, b.Booking_Time, b.Status
        FROM testdrive_bookings b
        JOIN Cars c ON b.Car_ID = c.Car_ID
        WHERE b.User_ID = %s
    """, (user_id,))
    testdrives = cursor.fetchall()

    cursor.execute("""
        SELECT s.Request_ID, c.Brand, c.Model, s.Request_Date, s.Description, s.Status
        FROM service_requests s
        JOIN Cars c ON s.Car_ID = c.Car_ID
        WHERE s.User_ID = %s
    """, (user_id,))
    services = cursor.fetchall()

    cursor.execute("""
        SELECT sa.Sale_ID, c.Brand, c.Model, sa.Sale_Date, sa.Payment_Mode, sa.Amount
        FROM sales sa
        JOIN Cars c ON sa.Car_ID = c.Car_ID
        WHERE sa.User_ID = %s
    """, (user_id,))
    purchases = cursor.fetchall()

    return render_template("my_activity.html", testdrives=testdrives, services=services, purchases=purchases)


@app.route("/delete_testdrive/<int:booking_id>")
@login_required
def delete_testdrive(booking_id):
    cursor.execute("DELETE FROM testdrive_bookings WHERE Booking_ID = %s", (booking_id,))
    db.commit()
    return redirect("/my_activity")

@app.route("/delete_service/<int:request_id>")
@login_required
def delete_service(request_id):
    cursor.execute("DELETE FROM service_requests WHERE Request_ID = %s", (request_id,))
    db.commit()
    return redirect("/my_activity")

@app.route("/delete_purchase/<int:sale_id>")
@login_required
def delete_purchase(sale_id):
    cursor.execute("DELETE FROM sales WHERE Sale_ID = %s", (sale_id,))
    db.commit()
    return redirect("/my_activity")



#ADMIN KA PART

@app.route("/admin")
@admin_required
def admin_dashboard():
    cursor.execute("SELECT COUNT(*) FROM Cars")
    total_cars = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM testdrive_bookings")
    total_bookings = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM service_requests")
    total_services = cursor.fetchone()['COUNT(*)']

    cursor.execute("SELECT COUNT(*) FROM sales")
    total_sales = cursor.fetchone()['COUNT(*)']

    return render_template('admin_home.html',
                           total_cars=total_cars,
                           total_bookings=total_bookings,
                           total_services=total_services,
                           total_sales=total_sales)

@app.route("/admin/Manage_Cars")
@admin_required
def manage_cars():
    cursor.execute("SELECT * FROM CARS")
    cars = cursor.fetchall()
    return render_template('manage_cars.html', cars=cars)

@app.route("/admin/update_stock/<int:car_id>", methods=["POST"])
@admin_required
def update_car_stock(car_id):
    action = request.form.get("action")

    if action == "increase":
        cursor.execute("UPDATE Cars SET Stock = Stock + 1 WHERE Car_ID = %s", (car_id,))
    elif action == "decrease":
        cursor.execute("UPDATE Cars SET Stock = GREATEST(Stock - 1, 0) WHERE Car_ID = %s", (car_id,))

    db.commit()
    return redirect("/admin/Manage_Cars")

@app.route("/admin/add_car", methods=["POST"])
@admin_required
def add_car():
    brand = request.form["brand"]
    model = request.form["model"]
    fuel = request.form["fuel_type"]
    trans = request.form["transmission"]
    price = request.form["price"]
    stock = request.form["stock"]

    cursor.execute("""
        INSERT INTO Cars (Brand, Model, Fuel_Type, Transmission, Price, Stock)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (brand, model, fuel, trans, price, stock))
    db.commit()
    return redirect("/admin/Manage_Cars")

@app.route("/admin/edit_car/<int:car_id>", methods=["GET", "POST"])
@admin_required
def edit_car(car_id):
    if request.method == "POST":
        brand = request.form["brand"]
        model = request.form["model"]
        fuel = request.form["fuel_type"]
        trans = request.form["transmission"]
        price = request.form["price"]
        stock = request.form["stock"]

        cursor.execute("""
            UPDATE Cars SET Brand=%s, Model=%s, Fuel_Type=%s,
            Transmission=%s, Price=%s, Stock=%s WHERE Car_ID=%s
        """, (brand, model, fuel, trans, price, stock, car_id))
        db.commit()
        return redirect("/admin/Manage_Cars")

    cursor.execute("SELECT * FROM Cars WHERE Car_ID = %s", (car_id,))
    car = cursor.fetchone()
    return render_template("edit_car.html", car=car)

@app.route("/admin/delete_car/<int:car_id>")
@admin_required
def delete_car(car_id):
    cursor.execute("DELETE FROM Cars WHERE Car_ID = %s", (car_id,))
    db.commit()
    return redirect("/admin/Manage_Cars")

@app.route("/admin/manage_showrooms")
@admin_required
def manage_showrooms():
    cursor.execute("SELECT * FROM showrooms")
    showrooms = cursor.fetchall()

    detailed_showrooms = []
    for s in showrooms:
        showroom_id = s["Showroom_ID"]

        # total cars
        cursor.execute("SELECT COUNT(*) as total FROM cars WHERE Showroom_ID = %s", (showroom_id,))
        total_cars = cursor.fetchone()["total"]

        # total orders
        cursor.execute("SELECT COUNT(*) as total FROM sales WHERE Car_ID IN (SELECT Car_ID FROM cars WHERE Showroom_ID = %s)", (showroom_id,))
        total_orders = cursor.fetchone()["total"]

        # pending service
        cursor.execute("""
            SELECT COUNT(*) as total FROM service_requests 
            WHERE Status = 'Pending' AND Car_ID IN (SELECT Car_ID FROM cars WHERE Showroom_ID = %s)
        """, (showroom_id,))
        pending_services = cursor.fetchone()["total"]

        # revenue
        cursor.execute("""
            SELECT COALESCE(SUM(Amount), 0) as revenue FROM sales 
            WHERE Car_ID IN (SELECT Car_ID FROM cars WHERE Showroom_ID = %s)
        """, (showroom_id,))
        revenue = cursor.fetchone()["revenue"]

        detailed = dict(s)
        detailed["total_cars"] = total_cars
        detailed["total_orders"] = total_orders
        detailed["pending_services"] = pending_services
        detailed["revenue"] = revenue

        detailed_showrooms.append(detailed)

    return render_template("manage_showrooms.html", showrooms=detailed_showrooms)


@app.route("/admin/add_showroom", methods=["POST"])
@admin_required
def add_showroom():
    name = request.form.get("name")
    location = request.form.get("location")
    Contact = request.form.get("Contact")
    email = request.form.get("email")

    cursor.execute("""
        INSERT INTO showrooms (Name, Location, Contact )
        VALUES (%s, %s, %s)
    """, (name, location, Contact))
    db.commit()

    return redirect("/admin/manage_showrooms")


@app.route("/admin/delete_showroom/<int:showroom_id>", methods=["POST"])
@admin_required
def delete_showroom(showroom_id):
    cursor.execute("DELETE FROM showrooms WHERE Showroom_ID = %s", (showroom_id,))
    db.commit()
    return redirect("/admin/manage_showrooms")

@app.route("/admin/manage_test")
@admin_required
def manage_test():
    cursor.execute("""
        SELECT tb.*, 
               u.USER_ID AS user_name, 
               CONCAT(c.Brand, ' ', c.Model) AS car_name
        FROM testdrive_bookings tb
        JOIN users u ON tb.User_ID = u.User_ID
        JOIN cars c ON tb.Car_ID = c.Car_ID
        ORDER BY Booking_Date DESC, Booking_Time
    """)
    bookings = cursor.fetchall()

    return render_template("manage_test.html", bookings=bookings)


@app.route("/admin/update_booking_status/<int:booking_id>", methods=["POST"])
@admin_required
def update_booking_status(booking_id):
    new_status = request.form.get("status")
    cursor.execute("UPDATE testdrive_bookings SET Status = %s WHERE Booking_ID = %s", (new_status, booking_id))
    db.commit()
    return redirect("/admin/manage_test")


@app.route("/admin/delete_booking/<int:booking_id>", methods=["POST"])
@admin_required
def delete_booking(booking_id):
    cursor.execute("DELETE FROM testdrive_bookings WHERE Booking_ID = %s", (booking_id,))
    db.commit()
    return redirect("/admin/manage_test")


@app.route("/admin/service_requests")
@admin_required
def manage_service_requests():
    cursor.execute("""
        SELECT sr.*, 
               u.User_ID, 
               CONCAT(c.Brand, ' ', c.Model) AS CarName
        FROM service_requests sr
        JOIN users u ON sr.User_ID = u.User_ID
        JOIN cars c ON sr.Car_ID = c.Car_ID
        ORDER BY sr.Request_Date DESC
    """)
    requests = cursor.fetchall()
    return render_template('manage_service.html', requests=requests)


@app.route("/admin/update_service_status/<int:request_id>", methods=["POST"])
@admin_required
def update_service_status(request_id):
    status = request.form.get("status")
    cursor.execute("UPDATE service_requests SET Status = %s WHERE Request_ID = %s", (status, request_id))
    db.commit()
    return redirect("/admin/service_requests")


@app.route("/admin/delete_service/<int:request_id>", methods=["POST"])
@admin_required
def delete_service_request(request_id):
    cursor.execute("DELETE FROM service_requests WHERE Request_ID = %s", (request_id,))
    db.commit()
    return redirect("/admin/service_requests")

@app.route("/admin/manage_user")
@admin_required
def manage_user_requests():
    cursor.execute("SELECT User_ID, Name, Email, Phone, Role FROM users WHERE Role != 'admin'")
    users = cursor.fetchall()
    return render_template("manage_user.html", users=users)


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    cursor.execute("DELETE FROM users WHERE User_ID = %s", (user_id,))
    db.commit()
    return redirect("/admin/manage_user")


@app.route("/admin/update_user_role/<int:user_id>", methods=["POST"])
@admin_required
def update_user_role(user_id):
    new_role = request.form.get("role")
    cursor.execute("UPDATE users SET Role = %s WHERE User_ID = %s", (new_role, user_id))
    db.commit()
    return redirect("/admin/manage_user")

    

if __name__ == "__main__":
    app.run(debug=True)
