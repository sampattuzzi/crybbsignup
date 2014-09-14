import os
import urllib
import cgi
import string
import random
import re

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import mail

import jinja2
import webapp2

################################################################################	
# Helper functions

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        
        
EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return EMAIL_RE.match(email)
################################################################################
	
def welcomeEmail(user_email, user_ID):
	mail.send_mail(sender="Crybb <victoria@crybb.com>",
              to="<"+user_email+">",
              subject="Thanks for Signing Up!",
              body="""
	Here at crybb, we like to reward sharing.
	
	Share the link below, and the more people who sign up through it, the earlier beta access you get!
	http://crybbviral.appspot.com/referral/"""+str(user_ID)+"""
	
	We will update you when your beta access is ready, but in the meantime find us on social media:
	http://www.facebook.com/wearecrybb
	http://www.twitter.com/wearecrybb
	
	Victoria,
	Founder, Crybb
	"""
	)
		
def createUser (user_email, user_location, user_refereeID):
	newUser = User(email=user_email,location=user_location,refereeID=user_refereeID,clicks=0,signups=0)
	newUser.put()
	
	if user_refereeID != "NULL":
		signupCount (user_refereeID)
	
	user_ID = newUser.key.id()
	welcomeEmail(user_email, user_ID)
	
	return newUser
	
def clickCount (uniqueID):
	referee=User.get_by_id(int(uniqueID))
	referee.clicks += 1
	referee.put()
	return referee.email
	
def signupCount (uniqueID):
	referee=User.get_by_id(int(uniqueID))
	referee.signups += 1
	referee.put()
	return referee.email
	
def emailExists (email):
	temp = User.query().filter(ndb.GenericProperty('email') == email).get()
	if temp:
		return temp.key.id()
	else:
		return 0
	
class User(ndb.Model):
	email = ndb.StringProperty()
	location = ndb.StringProperty()
	refereeID = ndb.StringProperty()
	clicks = ndb.IntegerProperty()
	signups = ndb.IntegerProperty()
	date = ndb.DateTimeProperty(auto_now_add=True)
	
class Landing(BlogHandler):
	def get(self):		
		self.render('landing.html', refereeID = 'NULL')		

		
class Progress(BlogHandler):
    def get(self):
		email = self.request.get('email', '')
		location = self.request.get('location', '')
		refereeID = self.request.get('refereeID', '')
		
		if emailExists(email):
			uniqueID = emailExists(email)
			currentUser = User.get_by_id(uniqueID)
			
		else:
			currentUser = createUser(email, location, refereeID)
			
		self.render('progress.html', user = currentUser)
		
class Referral(BlogHandler):
	def get(self,refereeID):
    
		clickCount(refereeID)
		
		self.render('landing.html', refereeID = refereeID)		

application = webapp2.WSGIApplication([
     webapp2.Route('/', handler=Landing),
     webapp2.Route('/progress', handler=Progress),
	 webapp2.Route('/referral/<refereeID>', handler=Referral),
	 ], debug=True)
