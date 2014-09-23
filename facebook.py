import urllib
import urlparse
import datetime
import json

class AuthenticationError(Exception):
    pass

class TokenExpired(Exception):
    pass

class PermissionError(Exception):
    pass


def get_login_url(app_id, return_url):
    args = urllib.urlencode({'client_id': app_id, 'redirect_uri': return_url}) 
    return "https://www.facebook.com/dialog/oauth?" + args


class AuthenticationToken:
    def __init__(self, token, expiry_date):
        self.raw_token = token
        self.expiry_date = expiry_date

    def has_expired(self):
        pass

    @classmethod
    def get_authentication_token_from_code(cls, app_id, app_secret, return_url):
        components = urlparse.urlparse(return_url)
        try:
            query = urlparse.parse_qs(components[4])
            original_return_url = urlparse.urlunparse((components[0], components[1], components[2], '', '', ''))
            code = query['code'][0]
            print code
            args = urllib.urlencode({
                'client_id': app_id, 
                'redirect_uri': original_return_url,
                'client_secret': app_secret,
                'code': code,
                })
        except KeyError:
            raise AuthenticationError("Bad return URL." ,return_url)
        print args
        response = urllib.urlopen("https://graph.facebook.com/oauth/access_token?" + args).read()

        query = urlparse.parse_qs(response)

        try:
            token = query['access_token'][0]
            expires = query['expires'][0]
            print expires
        except KeyError:
            raise AuthenticationError('Bad token response.', json.loads(response));

        return cls(token, datetime.datetime.now() + datetime.timedelta(seconds=int(expires)))

    def get_user(self):
        return FacebookUser(self)

    def __repr__(self):
        return "token: " + repr(self.raw_token) + ", expires: " + str(self.expiry_date)


class FacebookUser:
    def __init__(self, token):
        self.token = token

        if token.has_expired():
            raise TokenExpired(str(token.expiry_date))

        args = urllib.urlencode({'access_token': token.raw_token})
        response = urllib.urlopen("https://graph.facebook.com/me?" + args).read()
        data = json.loads(response)

        self.first_name = data.get('first_name', "")
        self.last_name = data.get('last_name', "")
        self.email = data.get('email')
        try:
            self.id = data['id']
            self.profile_url = data['link']
        except KeyError, e:
            raise PermissionError(e.args)

    def __repr__(self):
        return "id: " + str(self.id) + ", token: [" + repr(self.token) + "]"
