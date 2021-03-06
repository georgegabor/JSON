import os 
import webapp2 
import jinja2
import json
import logging
import datetime
from google.appengine.api import memcache
from signup import User
from datetime import datetime, timedelta
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=True)
query_time = datetime.now()
time_elapsed = 0

#~~~~~~~~~~~~~~~~~~~~~~~~ Memcache ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def cache_it(dbkey = 'joke'):
	contents = memcache.get(dbkey)
	if not contents:
		global query_time
		query_time = datetime.now()
		if dbkey is not 'joke':
			memcache.flush_all()
			contents = Content.get_by_id(int(dbkey))
			memcache.set(dbkey, contents)
		else:
			contents = db.GqlQuery("select * from Content order by created desc")
			contents = list(contents)
			memcache.set(dbkey, contents)
	this_moment = datetime.now()
	global time_elapsed
	time_elapsed = int((this_moment - query_time).total_seconds())
	return contents, time_elapsed

#~~~~~~~~~~~~~~~~~~~~~~~~ The Database Model ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Content(db.Model):
	subject = db.StringProperty(required=True)
	content = db.TextProperty(required=True)
	created = db.DateTimeProperty(auto_now_add=True)

	def make_dict(self):
		time_fmt = '%c'
		d = {	'subject': self.subject,
				'content': self.content,
				'created': self.created.strftime(time_fmt)}
		return d

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Handler Classes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#~~~~~~~~~~~~~~~~~~~~~~~~ Default Handler  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

	def render_json(self, d):
		json_txt = json.dumps(d)
		self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
		self.response.out.write(json_txt)

#~~~~~~~~~~~~~~~~~~~~~~~~  Frontpage Handler ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class MainPage(Handler):
	def render_front(self, contents=""):
		contents, time_elapsed = cache_it()
		self.render("content.html", contents=contents, time_elapsed=time_elapsed)

	def get(self):
		self.render_front()

#~~~~~~~~~~~~~~~~~~~~~~~~ Newpost Handler ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class NewPost(Handler):
	def render_newpost(self, subject="", contents="", error=""):
		self.render("blog.html", subject=subject , contents=contents , error=error)

	def get(self):
		self.render_newpost()

	def post(self):
		subject = self.request.get("subject")
		content = self.request.get("content")		

		if subject and content:
			a = Content(subject = subject, content = content)
			a.put()
			a_id = a.key().id()
			self.redirect("/%d" % a_id)
		else:
			error = "Subject and/or content missing ! Try again !"
			self.render_newpost(error=error)

#~~~~~~~~~~~~~~~~~~~~~~~~ Permalink Handler ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class PermaLink(Handler):
	def get(self, blog_id):
		s, time_elapsed = cache_it(dbkey = blog_id)
		self.render("permalink.html", content=s, time_elapsed=time_elapsed)

#~~~~~~~~~~~~~~~~~~~~~~~~ JSON Format Handlers ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class PageByIdJSON(Handler):
	def get(self, url_id):
		user_id = int(url_id.split(".")[0])
		user = Content.get_by_id(user_id)
		self.render_json(user.make_dict())

class FrontPageJSON(Handler):
    def get(self):
        posts = Content.all().order('-created')
        return self.render_json([p.make_dict() for p in posts])

#~~~~~~~~~~~~~~~~~~~~~~~~ Flush Handler ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Flush(Handler):
	def get(self):
		memcache.flush_all()
		global time_elapsed
		time_elapsed = 0
		self.redirect("/blog")

#~~~~~~~~~~~~~~~~~~~~~~~~ The Handler Handler :-) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

app = webapp2.WSGIApplication([ webapp2.Route(r'/blog', handler=MainPage),
    							webapp2.Route(r'/newpost', handler=NewPost),
    							webapp2.Route(r'/flush', handler=Flush),
    							webapp2.Route(r'/<:\d+.json>', handler=PageByIdJSON),
    							webapp2.Route(r'/.json', handler=FrontPageJSON),
    							webapp2.Route(r'/<:\d+>', handler=PermaLink)], debug = True)		