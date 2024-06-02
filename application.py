import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks=db.execute("SELECT * FROM person WHERE user=?",session.get("user_id"))
    cash=db.execute("SELECT cash FROM users WHERE id=?",session.get("user_id"))
    cash=int(cash[0]['cash'])
    total=cash
    for i in range(len(stocks)):
        stock=lookup(stocks[i]["symbol"])
        price=float(stock["price"])
        total+=price*stocks[i]["shares"]
        db.execute("UPDATE person SET price=? WHERE user =? AND symbol = ?",price,session.get("user_id"),stocks[i]["symbol"])
    return render_template("index.html",stock=stocks,total=usd(total),cash=usd(cash))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method=="GET":
        return render_template("buy.html")
    sym=request.form.get("symbol")
    if not sym:
        return apology("Symbol Can't be left empty")
    if not sym.isalpha():
        return apology("Enter Valid Symbol")

    share=float(request.form.get("shares"))
    if not (share and share>0 and share.is_integer()):
        return apology("Invalid quantity value. Please enter a Non-zero postive value.")
    stock=lookup(sym)
    if stock==None:
        return apology("Invalid Ticker Symbol")
    price=stock["price"]
    price=(float(price))
    cash=db.execute("SELECT cash FROM users WHERE id=?",session["user_id"])
    cash=float(cash[0]['cash'])

    print(cash)
    if price*share>cash:
        return render_template("buy.html",error="Not enough money in your wallet")
    else:
        sym_check=db.execute("SELECT * FROM person WHERE user= ?",session.get("user_id"))
        print(sym_check)
        if len(sym_check)!=0:
            share_hold=db.execute("SELECT shares from person WHERE user=? AND symbol=?",session.get("user_id"),stock["symbol"])
            if len(share_hold)==0:
                share_hold=0
            else:
                share_hold=float(share_hold[0]['shares'])
            print(share_hold)
            cash-=price*share
            share+=share_hold
            if share_hold==0:
                db.execute("INSERT INTO person (user,symbol,name,shares, price) VALUES(?,?,?,?,?)",session.get("user_id"),stock["symbol"],stock["name"],share,price)
            else:
                db.execute("UPDATE person SET shares=?,total=?,price=? WHERE user=? AND symbol=?",share,share*price+cash,price,session.get("user_id"),sym)
            db.execute("UPDATE users SET cash=? WHERE id=?",cash,session.get("user_id"))
            db.execute("INSERT INTO history (user,symbol,share,price,type) VALUES(?,?,?,?,?)",session.get("user_id"),stock["symbol"],float(request.form.get("shares")),price,"BUY");
            return redirect("/")
        db.execute("INSERT INTO person (user,symbol,name,shares, price) VALUES(?,?,?,?,?)",session.get("user_id"),stock["symbol"],stock["name"],share,price)
        cash-=price*share
        db.execute("UPDATE users SET cash=? WHERE id=?",cash,session.get("user_id"))
        db.execute("INSERT INTO history (user,symbol,share,price,type) VALUES(?,?,?,?,?)",session.get("user_id"),stock["symbol"],float(request.form.get("shares")),price,"BUY");
        return redirect("/")



@app.route("/history")
@login_required
def history():
    history=db.execute("SELECT * FROM history WHERE user=?",session.get("user_id"))
    return render_template("history.html",history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method=="GET":
        return render_template("quote.html")
    sym=request.form.get("symbol")
    if not sym:
        return apology("Symbol Field Can't be Left Empty")
    stock=lookup(sym)
    if stock==None:
        return apology("Stock Not found. Please enter correct Symbol")
    return render_template("quoted.html",name=stock["name"],price=stock["price"],symbol=stock["symbol"])




@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method=="GET":
        return render_template("register.html")
    count = db.execute("SELECT COUNT(*) FROM users WHERE username = ?", request.form.get("username"))
    if count[0]["COUNT(*)"]==0:
        name=request.form.get("username")
        if not name:
            return apology("Enter Username")
    else:
        return apology("Duplicate Username")

    password=request.form.get("password")
    confirmation=request.form.get("confirmation")
    if not password:
        return apology("Enter Password")
    if not confirmation:
        return apology("Enter Password Again")
    if confirmation!=password:
        return apology("Password Mismatch")
    pass_hash=generate_password_hash(password)
    db.execute("INSERT INTO users (username,hash) VALUES(?,?)",name,pass_hash)
    return render_template("/login.html",message="You are registered. Enter your username and password to Login")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method=="GET":
        stocks=db.execute("SELECT * FROM person WHERE user=?",session.get("user_id"))
        return render_template("sell.html",stocks=stocks)
    sym=request.form.get("symbol")
    if not sym:
        return render_template("sell.html",error="Please Select a Share to Sell")
    share=float(request.form.get("shares"))
    if share<=0:
        return render_template("sell.html",error="Number of shares must be greater than zero")
    share_hold=db.execute("SELECT shares from person WHERE user=? AND symbol=?",session.get("user_id"),sym)
    if len(share_hold)==0:
        share_hold=0
    else:
        share_hold=float(share_hold[0]['shares'])
    if share>share_hold:
        return render_template("sell.html",error="Not enough shares")
    share_hold-=share
    price=float(lookup(sym)["price"])
    db.execute("UPDATE person SET shares=?,price=? WHERE user=? AND symbol=?",share_hold,price,session.get("user_id"),sym)
    db.execute("INSERT INTO history (user,symbol,share,price,type) VALUES(?,?,?,?,?)",session.get("user_id"),sym,float(request.form.get("shares")),usd(price),"SELL");
    cash_hold=db.execute("SELECT cash FROM users WHERE id=?",session.get("user_id"))
    cash_hold=float(cash_hold[0]['cash'])
    cash=price*share+cash_hold
    db.execute("UPDATE users SET cash=? WHERE id=?",cash,session.get("user_id"))
    db.execute("DELETE FROM person WHERE shares=0")
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
