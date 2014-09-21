from google.appengine.ext import ndb

class User(ndb.Model):
    email = ndb.StringProperty(required=False)
    location = ndb.StringProperty()
    refereeID = ndb.StringProperty()
    clicks = ndb.IntegerProperty()
    signups = ndb.IntegerProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    name = ndb.StringProperty(required=True)
    profile_url = ndb.StringProperty(required=True)
    access_token = ndb.StringProperty(required=True)

def clickCount (uniqueID):
    referee=User.get_by_id(str(uniqueID))
    referee.clicks += 1
    referee.put()
    return referee.email

@ndb.transactional
def signupCount (uniqueID):
    referee=User.get_by_id(str(uniqueID))
    referee.signups += 1
    referee.put()
    return referee.email

class Configuration(ndb.Model):
    fb_id = ndb.StringProperty()
    fb_secret = ndb.StringProperty()

def get_config():
    config = Configuration.get_by_id(1)
    if not config:
        config = Configuration(id=1, fb_id="", fb_secret="")
        config.put()
    return config

def get_facebook_id():
    return get_config().fb_id

def get_facebook_secret():
    return get_config().fb_secret

