from datetime import datetime
from flask import Flask, render_template, flash, redirect, url_for, session, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, validators, TextAreaField
from passlib.handlers.sha2_crypt import sha256_crypt
from functools import wraps
from slugify import slugify

from wtforms.fields.simple import TextAreaField


app = Flask(__name__,static_url_path='/static')
app.secret_key = "tkblog"

# mysql settings
mysql = MySQL(app)
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "tkblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

# user register, login, article add form, page form
class RegisterForm(Form):
    name = StringField("Name and Surname", validators=[validators.Length(min= 3, max= 25), validators.DataRequired()])
    username = StringField("Username", validators=[validators.Length(min= 3, max= 35), validators.DataRequired()])
    email = StringField("Email", validators=[validators.DataRequired(), validators.Email("Please enter a valid email address")])
    password = PasswordField("Password", validators=[
        validators.Length(min= 8, max= 40),
        validators.DataRequired(),
        validators.EqualTo(fieldname="confirm",message="Password does not match")
        ])
    confirm = PasswordField("Re-enter your password", validators=[validators.DataRequired()])

class LoginForm(Form):
    username = StringField("Username",validators=[validators.DataRequired()])
    password = PasswordField("Password",validators=[validators.DataRequired()])

class ArticleForm(Form):
    title = StringField("Title", validators=[validators.Length(min=10, max=255), validators.DataRequired()])
    content = TextAreaField("Content", validators=[validators.Length(min=100), validators.DataRequired()])
    thumbnail = StringField("Thumbnail", default="/static/img/default.png")

class PageForm(Form):
    title = StringField("Title", validators=[validators.Length(min=5, max=255), validators.DataRequired()])
    content = TextAreaField("Content", validators=[validators.Length(min=50), validators.DataRequired()])

# routes
@app.route("/")
def index():
    cursor = mysql.connection.cursor()
    article_query = "Select * From articles ORDER BY id DESC LIMIT 3"
    result = cursor.execute(article_query)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("index.html", articles = articles)
    else:
        return render_template("index.html")

# login control decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash(message="You must login first to view the page.", category="warning")
            return redirect(url_for("login"))
    return decorated_function

# dashboard

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route('/dashboard/articles')
@login_required
def dashboard_articles():
    cursor = mysql.connection.cursor()
    article_query = "Select * From articles where author = %s ORDER BY id DESC"
    result = cursor.execute(article_query,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard-articles.html", articles = articles)
    else:
        return render_template("dashboard.html")

@app.route('/dashboard/pages')
@login_required
def dashboard_pages():
    cursor = mysql.connection.cursor()
    article_query = "Select * From pages ORDER BY id DESC"
    result = cursor.execute(article_query)
    if result > 0:
        pages = cursor.fetchall()
        return render_template("dashboard-pages.html", pages = pages)
    else:
        return render_template("dashboard.html")


# pages

@app.route('/page/<slug>-<int:id>')
def page_detail(slug, id):
    cursor = mysql.connection.cursor()
    page_query = "Select * From pages where slug = %s and id = %s"
    result = cursor.execute(page_query,(slug, id))
    if result > 0:
        page = cursor.fetchone()
        return render_template("page.html", page = page)
    else:
        return render_template("page-error.html")

@app.route('/add-page', methods = ["GET", "POST"])
@login_required
def page_add():
    form = PageForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        slug = slugify(form.title.data)
        cursor = mysql.connection.cursor()
        add_query = "Insert into pages(title,content,slug) VALUES(%s,%s,%s)"
        cursor.execute(add_query,(title, content, slug))
        mysql.connection.commit()
        cursor.close()
        flash(message="The page has been successfully added.", category="success")
        return redirect(url_for("dashboard_pages"))
    return render_template("add-page.html", form = form)

@app.route('/delete/page/<string:id>')
@login_required
def page_delete(id):
    cursor = mysql.connection.cursor()
    page_query = "Select * From pages Where id = %s"
    result = cursor.execute(page_query,(id,))
    if result > 0:
        delete_query = "Delete From pages where id = %s"
        cursor.execute(delete_query,(id,))
        mysql.connection.commit()
        flash(message="The page was successfully deleted", category="success")
        return redirect(url_for("dashboard"))
    else:
        flash(message="There is no such page or you do not have permission to delete it.", category="danger")
        return redirect(url_for("dashboard_pages"))

@app.route('/edit/page/<string:id>', methods=["GET","POST"])
@login_required
def page_update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        article_query = "Select * From pages where id = %s"
        result = cursor.execute(article_query, (id,))
        if result > 0:
            page = cursor.fetchone()
            form = PageForm()
            form.title.data = page["title"]
            form.content.data = page["content"]
            return render_template("update-page.html", form = form)
        else:
            flash(message="There is no such page or you do not have permission to delete it.", category="danger")
            return redirect(url_for("dashboard_pages"))
    else:
        form = PageForm(request.form)
        if form.validate():
            updated_title = form.title.data
            updated_content = form.content.data
            updated_slug = slugify(form.title.data)        
            update_query = "Update pages Set title = %s, content = %s, slug = %s where id = %s"
            cursor = mysql.connection.cursor()
            cursor.execute(update_query, (updated_title, updated_content, updated_slug, id))
            mysql.connection.commit()
            flash(message="The page was successfuly updated", category="success")
            return redirect(url_for("dashboard_pages"))
        else:
            flash(message="Something went wrong.", category="danger")
            return redirect(url_for("dashboard_pages"))

# Global pages
@app.context_processor
def get_pages():
    cursor = mysql.connection.cursor()
    page_query = "Select * From pages"
    result = cursor.execute(page_query)
    if result > 0:
        pages_navbar = cursor.fetchall()
        return dict(pages_navbar = pages_navbar)


# articles

@app.route('/articles')
def articles():
    cursor = mysql.connection.cursor()
    article_query = "Select * From articles ORDER BY id DESC"
    result = cursor.execute(article_query)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

@app.route('/add-article', methods=["GET","POST"])
@login_required
def add_article():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        thumbnail = form.thumbnail.data
        # now = datetime.now()
        # slug = slugify(form.title.data + "-" + str(now.day) + str(now.month) + str(now.microsecond))
        slug = slugify(form.title.data)
        cursor = mysql.connection.cursor()
        add_query = "Insert into articles(title,author,content,post_thumbnail,slug) VALUES(%s,%s,%s,%s, %s)"
        cursor.execute(add_query,(title,session["username"], content, thumbnail, slug))
        mysql.connection.commit()
        cursor.close()
        flash(message="The article has been successfully added.", category="success")
        return redirect(url_for("dashboard"))
    return render_template("add-article.html", form = form)



@app.route('/article/<int:id>-<slug>')
def article_detail(slug, id):
    cursor = mysql.connection.cursor()
    article_query = "Select * From articles where slug = %s and id = %s"
    result = cursor.execute(article_query,(slug, id))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article-error.html")

@app.route('/delete/article/<string:id>')
@login_required
def article_delete(id):
    cursor = mysql.connection.cursor()
    article_query = "Select * From articles Where author = %s and id = %s"
    result = cursor.execute(article_query,(session["username"], id))
    if result > 0:
        delete_query = "Delete From articles where id = %s"
        cursor.execute(delete_query,(id,))
        mysql.connection.commit()
        flash(message="Article successfully deleted", category="success")
        return redirect(url_for("dashboard"))
    else:
        flash(message="There is no such article or you do not have permission to delete it.", category="danger")
        return redirect(url_for("dashboard"))

@app.route('/edit/article/<string:id>', methods=["GET","POST"])
@login_required
def article_update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        article_query = "Select * From articles where author = %s and id = %s"
        result = cursor.execute(article_query, (session["username"], id))
        if result > 0:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            form.thumbnail.data = article["post_thumbnail"]
            return render_template("update-article.html", form = form)
        else:
            flash(message="There is no such article or you do not have permission to delete it.", category="danger")
            return redirect(url_for("dashboard"))
    else:
        form = ArticleForm(request.form)
        if form.validate():
            updated_title = form.title.data
            updated_content = form.content.data
            updated_thumbnail = form.thumbnail.data
            updated_slug = slugify(form.title.data)        
            update_query = "Update articles Set title = %s, content = %s, post_thumbnail = %s, slug = %s where id = %s"
            cursor = mysql.connection.cursor()
            cursor.execute(update_query, (updated_title, updated_content, updated_thumbnail, updated_slug, id))
            mysql.connection.commit()
            flash(message="The article successfuly updated", category="success")
            return redirect(url_for("dashboard"))
        else:
            flash(message="Something went wrong.", category="danger")
            return redirect(url_for("dashboard"))

# Global articles
@app.context_processor
def get_articles():
    cursor = mysql.connection.cursor()
    article_query = "Select * From articles ORDER BY id DESC LIMIT 3"
    result = cursor.execute(article_query)
    if result > 0:
        article_everywhere = cursor.fetchall()
        return dict(article_everywhere = article_everywhere)


# login register logout

@app.route('/register', methods = ["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        user_query = "Insert into users(name,username,email,password) VALUES(%s, %s, %s, %s)"
        cursor.execute(user_query, (name, username, email, password))
        mysql.connection.commit()
        cursor.close()
        flash(message="You have successfully registered.", category= "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form = form)
    
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST" and form.validate():
        username = form.username.data
        password = form.password.data
        cursor = mysql.connection.cursor()
        user_query = "Select * From users where username = %s"
        result = cursor.execute(user_query, (username,))
        if result > 0:
            data = cursor.fetchone()
            user_password = data["password"]
            if sha256_crypt.verify(password, user_password):
                flash(message="Welcome :)", category="success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Password is wrong!", category="danger")
                return redirect(url_for("login"))
        else:
            flash(message="Username is wrong!", category="danger")
            return redirect(url_for("login"))
    return render_template("login.html", form = form)

@app.route('/logout')
def logout():
    session.clear()
    flash(message="You logged out successfully, we wait again.", category="success")
    return redirect(url_for("index"))

# search

@app.route('/search', methods=["GET","POST"])
def search():
    if request.method == "GET":
       return render_template("search.html")
    else:
        search_key = request.form.get("search-key")
        cursor = mysql.connection.cursor()
        search_query = "Select * From articles where title LIKE '%" + search_key + "%' or content LIKE '%" + search_key + "%' "
        result = cursor.execute(search_query)
        if result > 0:
            articles = cursor.fetchall()
            flash(message= "Showing results for \"" + search_key + "\"", category="success")
            return render_template("articles.html", articles = articles)
        else:
            flash(message="There is no article related to the content you are looking for.", category="secondary")
            return render_template("search.html")

if __name__ == '__main__':
    app.run(debug=True)
