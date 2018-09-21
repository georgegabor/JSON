import os
import webapp2
import validate
import jinja2
import hashlib
import hmac
from  string import letters
from google.appengine.ext import db


secret = u"687897689^&2"

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)
################################################## BaseHandler for Jinja #################################################################################
class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))
################################################## Hashing + Register function #################################################################################
class Secret(Handler):
	# make_salt is not used, but i leave it here :-)
	def make_salt():
		return ''.join(random.choice(letters) for x in xrange(5))

	@staticmethod	
	def hash_password(password):
		return hashlib.sha256(password).hexdigest()

	@staticmethod
	def hash_cookie(val):
		return '%s|%s' % (val, hmac.new(str(secret), str(val)).hexdigest())	

	# Would have been better to put the register method in the Database class 'User'
	@staticmethod
	def register( username, password, email):
		hashed_password = Secret.hash_password(password)
		new_user = User( username = username, password = hashed_password, email = email )
		new_user.put()
		userid = str(new_user.key().id())
		cookie = Secret.hash_cookie(userid)
		return cookie
################################################## The Database Model #################################################################################
class User(db.Model):
	username = db.StringProperty( required = True )
	password = db.StringProperty( required = True )
	email = db.StringProperty()
################################################## The SignUp Handler #################################################################################
# This class seems a bit messy to me, could use some refactoring to make it a cleaner. But it works ! At least on my laptop :-) 
class Signup(Handler):
	def render_signup(self, usernameerror = "", passworderror = "", verifyerror = "", emailerror = "", 
							username = "", password = "", verify = "", email = ""):

		self.render("signupform.html", 
					usernameerror = usernameerror,
					passworderror = passworderror,
					verifyerror = verifyerror,
					emailerror = emailerror,
					username = username,
					password = password,
					verify = verify,
					email = email )

	def get(self):
		self.render_signup()

	def post(self):
		usernameerror = ""
		passworderror = ""
		verifyerror = ""
		emailerror = ""
		username = self.request.get('username')
		password = self.request.get('password')
		verify = self.request.get('verify')
		email = self.request.get('email')
		validUsername = validate.validUsername(username)
		validPassword = validate.validPassword(password)
		validVerify = validate.validVerify(verify,password)
		validEmail = validate.validEmail(email)

		u = User.all().filter('username', username ).get()
		if not u: 
			if (validUsername and validPassword and validVerify and validEmail):			
				new_user = Secret.register(username, password, email)
				print new_user
				self.response.set_cookie( key = 'userid', value = new_user, path = '/')
				self.redirect("/welcome", username)
				
			else:
				if (not validUsername):
					usernameerror="That's not a valid username."
				if (not validPassword):
					passworderror="That not a valid password."
				if (validPassword and not validVerify):
					verifyerror="Your passwords didn't match."
				if (not validEmail):
					emailerror="That's not a valid email."
				self.render_signup(usernameerror= usernameerror, passworderror= passworderror, verifyerror= verifyerror, 
									emailerror= emailerror, username= username, email= email)
		else:
			self.render_signup(usernameerror = "User already exists !")				
##################################################  The Welcome Handler #################################################################################
class Welcome(webapp2.RequestHandler):
	def get(self):
		cookie_value = self.request.cookies.get('userid')
		if not cookie_value:
			self.redirect(r"/signup")
		else:			
			user_id = int(cookie_value.split("|")[0])
			user = User.get_by_id(user_id)
			print cookie_value
			print user_id
			self.response.out.write("<br />Welcome  %s" % user.username )
		
##################################################  The Login Handler #################################################################################
class Login(Handler):
	def get(self):
		self.render("login.html", usernameerror = "", passworderror = "")

	def post(self):
		username = self.request.get('username')
		password = Secret.hash_password(self.request.get('password'))

		user = User.all().filter('username', username ).get()
		if not user:	
			error = "User doesn't exist !!!"
			self.render("login.html", usernameerror = error )
		else:
			if user.password == password:
				userid = str(user.key().id())
				cookie = Secret.hash_cookie(userid)
				self.response.set_cookie( key = 'userid', value = cookie, path = '/')
				self.redirect("/welcome")				
			else:
				error = "Passwort stimmt nicht !!!"	
				self.render("login.html", passworderror = error )
##################################################  The Logout Handler #################################################################################
class Logout(Handler):
	def get(self):
		self.response.set_cookie( key = 'userid', value = None, path = '/')
		self.redirect(r"/signup")
##################################################  #################################################################################
app = webapp2.WSGIApplication([ webapp2.Route(r'/signup', handler=Signup),
								webapp2.Route(r'/welcome', handler=Welcome),
    							webapp2.Route(r'/login', handler=Login),
    							webapp2.Route(r'/logout', handler=Logout)],
								debug = True)		