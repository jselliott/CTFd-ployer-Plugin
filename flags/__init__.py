import re
import json
import time
from CTFd.plugins import register_plugin_assets_directory
from CTFd.utils.user import get_current_user
from CTFd.models import Users, Challenges
from CTFd.utils import get_config
import requests


class FlagException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class BaseFlag(object):
    name = None
    templates = {}

    @staticmethod
    def compare(self, saved, provided):
        return True


class CTFdStaticFlag(BaseFlag):
    name = "static"
    templates = {  # Nunjucks templates used for key editing & viewing
        "create": "/plugins/flags/assets/static/create.html",
        "update": "/plugins/flags/assets/static/edit.html",
    }

    @staticmethod
    def compare(chal_key_obj, provided):
        saved = chal_key_obj.content
        data = chal_key_obj.data

        if len(saved) != len(provided):
            return False
        result = 0

        if data == "case_insensitive":
            for x, y in zip(saved.lower(), provided.lower()):
                result |= ord(x) ^ ord(y)
        else:
            for x, y in zip(saved, provided):
                result |= ord(x) ^ ord(y)
        return result == 0


class CTFdRegexFlag(BaseFlag):
    name = "regex"
    templates = {  # Nunjucks templates used for key editing & viewing
        "create": "/plugins/flags/assets/regex/create.html",
        "update": "/plugins/flags/assets/regex/edit.html",
    }

    @staticmethod
    def compare(chal_key_obj, provided):
        saved = chal_key_obj.content
        data = chal_key_obj.data

        try:
            if data == "case_insensitive":
                res = re.match(saved, provided, re.IGNORECASE)
            else:
                res = re.match(saved, provided)
        # TODO: this needs plugin improvements. See #1425.
        except re.error as e:
            raise FlagException("Regex parse error occured") from e

        return res and res.group() == provided

# Flags created dynamically per-player
class CTFdDynamicFlag(BaseFlag):
    name = "dynamic"
    templates = {  # Nunjucks templates used for key editing & viewing
        "create": "/plugins/flags/assets/dynamic/create.html",
        "update": "/plugins/flags/assets/dynamic/edit.html",
    }

    @staticmethod
    def compare(chal_key_obj, provided):
        saved = chal_key_obj.content
        data = chal_key_obj.data

        if len(saved) != len(provided):
            return False
        
        try:
            player_id = int(data)
        except ValueError:
            return False

        # If the provided flag matches the saved flag
        if saved == provided:

            user = get_current_user()

            # This flag isn't assigned to this user (log flag sharing)
            if user.id != player_id:
                
                owner = Users.query.get(player_id)
                challenge = Challenges.query.get(chal_key_obj.challenge_id)
                webhook = get_config("DEPLOYER_FLAG_SHARING_WEBHOOK",None)
                if owner and challenge and webhook:
                    message = "🚩 FLAG SHARING ALERT! 🚩 %s attempted to enter a flag owned by %s for challenge '%s'" % (user.name, owner.name, challenge.name)
                    requests.post(webhook,json={"content":message})


                return False

            return True
        
        return False

FLAG_CLASSES = {"static": CTFdStaticFlag, "regex": CTFdRegexFlag, "dynamic": CTFdDynamicFlag}


def get_flag_class(class_id):
    cls = FLAG_CLASSES.get(class_id)
    if cls is None:
        raise KeyError
    return cls


def load(app):
    register_plugin_assets_directory(app, base_path="/plugins/flags/assets/")
