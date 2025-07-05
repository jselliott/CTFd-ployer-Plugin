from CTFd.utils import get_config
from CTFd.models import Challenges, Users, Flags
from CTFd.models import db
import requests
import logging
import time
import random
import hashlib
import json
from CTFd.plugins.deployer.models import DeployerChallenge, DeployerInstance, FlagShares

def list_instances():
    return DeployerInstance.query.filter(DeployerInstance.expires >= int(time.time())).all()

def list_instances_in_host():

    challenge_host = get_config("DEPLOYER_CHALLENGE_HOST")

    if challenge_host is None:
        return []

    try:
        R = requests.get(f"{challenge_host}/containers")
        logging.info("Fetched containers: %d" % len(R.json()))

        return R.json()
    
    except Exception as e:
        logging.error(e)
        return []

def launch_instance(player_id,challenge_id):

    challenge_host = get_config("DEPLOYER_CHALLENGE_HOST")
    dynamic_flags = get_config("DEPLOYER_DYNAMIC_FLAGS","No")
    flag_prefix = get_config("DEPLOYER_FLAG_PREFIX","flag")

    if challenge_host is None:
        return False
    
    dep = DeployerChallenge.query.filter_by(chalid=challenge_id).first()

    if dep is None:
        return False
    
    expires = int(time.time())+int(dep.timeout)
    
    data = {"image":dep.image,"port":str(dep.port),"challenge_id":str(challenge_id),"player_id":str(player_id),"expires":str(expires)}

    if dynamic_flags == "Yes":

        flag_hash = hashlib.md5(random.randbytes(20)).hexdigest()
        data["flag"] = "%s{%s}" % (flag_prefix,flag_hash)
        
    try:

        response = requests.post(f"{challenge_host}/launch",json=data).json()
        
        new_instance = DeployerInstance(dcid=dep.id,
                                        playerid=player_id,
                                        expires=str(expires),
                                        fqdn=response["url"],
                                        container=response["container"][:12])
            
        db.session.add(new_instance)
        db.session.commit()

        # Add dynamic flag record for this challenge
        if dynamic_flags == "Yes":

            new_flag = Flags(challenge_id=challenge_id,
                         type="dynamic",
                         content=data["flag"],
                         data=str(player_id))
            
            db.session.add(new_flag)
            db.session.commit()

        return {"fqdn":response["url"],"expires":expires,"container":response["container"][:12]}

    except Exception as e:

        return {"error":str(e)}
    
def get_deployer_challenges():
    return DeployerChallenge.query.all()
    

def kill_player_container(player_id,challenge_id):

    challenge_host = get_config("DEPLOYER_CHALLENGE_HOST")

    if challenge_host is None:
        return False

    return requests.post(f"{challenge_host}/stop",json={"player_id":str(player_id),"challenge_id":str(challenge_id)}).json()

def kill_container(container_id):

    challenge_host = get_config("DEPLOYER_CHALLENGE_HOST")

    if challenge_host is None:
        return False

    return requests.post(f"{challenge_host}/stop_container",json={"container_id":container_id}).json()

def kill_all_by_player(player_id):

    challenge_host = get_config("DEPLOYER_CHALLENGE_HOST")

    if challenge_host is None:
        return False
    
    return requests.post(f"{challenge_host}/killall",json={"player_id":player_id}).json()

def log_flag_sharing(challenge_id, belongstoid, enteredbyid):

    fs = FlagShares(challenge_id=challenge_id,
                    belongstoid=belongstoid,
                    enteredbyid=enteredbyid,
                    timestamp=int(time.time()))
    db.session.add(fs)
    db.session.commit()