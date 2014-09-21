import os
import urllib
import cgi
import string
import random
import re

from google.appengine.api import mail

import jinja2
import webapp2
from webapp2_extras import sessions

#Third party libraries
import sys
lib_dir = "libs"
sys.path += [os.path.join(lib_dir, name) for name in os.listdir(lib_dir)
            if os.path.isdir(os.path.join(lib_dir, name))] #Add subdirectories of 'libs' to path
import facebook
from models import User, get_facebook_id, get_facebook_secret, clickCount, signupCount

def set_trace():
    import pdb, sys
    debugger = pdb.Pdb(stdin=sys.__stdin__, 
        stdout=sys.__stdout__)
    debugger.set_trace(sys._getframe().f_back)

################################################################################    
# Helper functions

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class BaseHandler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)

    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        return self.session_store.get_session()

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return EMAIL_RE.match(email)
################################################################################
    
def welcomeEmail(user_email, user_ID):
    mail.send_mail(sender="Crybb <sam.pattuzzi@googlemail.com>",
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
        
def createUser (user, user_location, user_refereeID):
    
    newUser = User(
            id=str(user.id),
            name=(user.first_name + " " + user.last_name), #todo: should be seperate fields
            email=user.email,
            profile_url=user.profile_url,
            location=user_location,
            refereeID=user_refereeID,
            clicks=0,
            signups=0,
            access_token=user.token.raw_token,
            )
    newUser.put()
    
    if user_refereeID != "NULL":
        signupCount (user_refereeID)
    
    user_ID = newUser.key.id()
    welcomeEmail(user.email, user_ID)
    
    return newUser

def emailExists (email):
    temp = User.query().filter(ndb.GenericProperty('email') == email).get()
    if temp:
        return temp.key.id()
    else:
        return 0
    
class Landing(BaseHandler):
    def get(self): 

        self.render('landing.html', 
                refereeID = 'NULL', 
                redirect_url=facebook.get_login_url(get_facebook_id(), webapp2.uri_for('progress', _full=True)))     

class Progress(BaseHandler):
    def get(self):

        user = None
        message = None

        if 'user' in self.session:
            user = User.get_by_id(self.session["user"])

            if not user:
                message = "You do not appear to be logged in."

        else:
            fb_user = None

            try:
                token = facebook.AuthenticationToken.get_authentication_token_from_code(
                        app_id=get_facebook_id(), 
                        app_secret=get_facebook_secret(), 
                        return_url=self.request.url,
                        )
                fb_user = token.get_user()

            except facebook.AuthenticationError:
                message = "Oops, there appears to have been an authentication error. Please try again."

            except facebook.PermissionError:
                #todo: Prompt for permissions again
                message = "Looks like you didn't give us all the permissions we require. We won't be able to subscribe you." 

            if fb_user:
                user = createUser(fb_user, "", "NULL") #Get these in another step of sign-up
                self.session['user'] = str(fb_user.id)
        
        self.render('progress.html', fb_app_id = get_facebook_id(), user = user, message = message)       
        
class Referral(BaseHandler):
    def get(self,refereeID):
        
        clickCount(refereeID)
        
        self.render('landing.html', refereeID = refereeID)      

class WireFrame(BaseHandler):
    def get(self):
        self.render('wireframe.html')      

config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': str(get_facebook_secret()),
}
    
application = webapp2.WSGIApplication([
     webapp2.Route('/', handler=Landing, name="landing"),
     webapp2.Route('/progress', handler=Progress, name="progress"),
     webapp2.Route('/referral/<refereeID>', handler=Referral, name="referral"),
     webapp2.Route('/wireframe', handler=WireFrame),
     ], 
     debug=True,
     config=config
     )
