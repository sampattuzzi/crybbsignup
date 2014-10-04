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
        kw['flashes'] = self.session.get_flashes()
        print kw
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

    @webapp2.cached_property
    def user(self):
        user = None

        if 'user' in self.session:
            user = User.get_by_id(self.session["user"])

            if not user:
                self.session.add_flash("You do not appear to be logged in.")

        return user

    def createUser (self, user, email_verified, user_location, user_refereeID):
        
        newUser = User(
                id=str(user.id),
                name=(user.first_name + " " + user.last_name), #todo: should be seperate fields
                email=user.email,
                email_verified=email_verified,
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
        if user.email:
            self.welcomeEmail(user.email, user_ID)
        
        return newUser

    def welcomeEmail(self, user_email, user_ID):
        body = """
        Here at crybb, we like to reward sharing.
        
        Share the link below, and the more people who sign up through it, the earlier beta access you get!
        """+application.router.build(self.request, 'referral', (), {'refereeID': str(user_ID),'_full': True})+"""
        
        We will update you when your beta access is ready, but in the meantime find us on social media:
        http://www.facebook.com/wearecrybb
        http://www.twitter.com/wearecrybb
        
        Victoria,
        Founder, Crybb
        """
        print body

        mail.send_mail(sender="Crybb <sam.pattuzzi@googlemail.com>",
                  to="<"+user_email+">",
                  subject="Thanks for Signing Up!",
                  body=body)


EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return EMAIL_RE.match(email)
################################################################################
    
        
def emailExists (email):
    temp = User.query().filter(ndb.GenericProperty('email') == email).get()
    if temp:
        return temp.key.id()
    else:
        return 0
    
class Landing(BaseHandler):
    def prepare_page(self, refereeID):
        self.render('landing.html', 
                refereeID = refereeID,
                redirect_url = webapp2.uri_for('stageone'))     

    def get(self): 
        self.prepare_page('NULL')

class Referral(Landing):
    def get(self,refereeID):
        
        clickCount(refereeID)
        
        self.prepare_page(refereeID)


class Progress(BaseHandler):
    def get(self):
        referral_link = None
        if not self.user:
            self.session.add_flash("You are not logged in.")
        else:
            referral_link = application.router.build(self.request, 'referral', (), {'refereeID': self.user.key.id(),'_full': True})

        self.render('progress.html', 
                user=self.user, 
                referral_link=referral_link)

#Login stages

class StageOne(BaseHandler):
    def get(self):
        location = self.request.get('location')
        refereeID = self.request.get('refereeID')

        if not (location and refereeID):
            self.write('Bad form data.')
            return
        
        self.session['location'] = location
        self.session['refereeID'] = refereeID

        self.redirect(facebook.get_login_url(get_facebook_id(), webapp2.uri_for('stagetwo', _full=True)))

class StageTwo(BaseHandler):
    def get(self):
        fb_user = None

        try:
            token = facebook.AuthenticationToken.get_authentication_token_from_code(
                    app_id=get_facebook_id(), 
                    app_secret=get_facebook_secret(), 
                    return_url=self.request.url,
                    )
            fb_user = token.get_user()

        except facebook.AuthenticationError:
            self.session.add_flash("Oops, there appears to have been an authentication error. Please try again.")
            self.redirect_to('landing') #todo: save referal in cookie so that we have it at this stage.
            return

        except facebook.PermissionError:
            #todo: Prompt for permissions again
            self.session.add_flash("Looks like you didn't give us all the permissions we require. We won't be able to subscribe you.")

        if fb_user:
            existing_user = User.get_by_id(str(fb_user.id))
            location = self.session.get('location')
            refereeID = self.session.get('refereeID')

            if existing_user:
                user = existing_user
                user.location = location
                user.put()
            else:
                email_verified = (fb_user.email != None) #emails from FB are automatically verified.
                user = self.createUser(fb_user, email_verified, location, refereeID) #Get these in another step of sign-up
            
            self.session['user'] = str(user.key.id())

        if not self.user.email:
            self.redirect_to('get_email')
            return

        self.redirect_to('progress')

class GetEmail(BaseHandler):
    def get(self):
        self.render('get_email.html', action_url = self.uri_for('get_email'))

    def post(self):
        user = self.user
        user.email = self.request.get('email')
        user.email_verified = False
        self.welcomeEmail(user.email, str(user.key.id()))
        user.put()
        self.redirect_to('progress')


config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': str(get_facebook_secret()),
}
    
application = webapp2.WSGIApplication([
     webapp2.Route('/', handler=Landing, name="landing"),
     webapp2.Route('/progress', handler=Progress, name="progress"),
     webapp2.Route('/stageone', handler=StageOne, name="stageone"),
     webapp2.Route('/stagetwo', handler=StageTwo, name="stagetwo"),
     webapp2.Route('/get_email', handler=GetEmail, name="get_email"),
     webapp2.Route('/referral/<refereeID>', handler=Referral, name="referral"),
     ], 
     debug=True,
     config=config
     )
