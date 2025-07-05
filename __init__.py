from flask import Blueprint, render_template, request, redirect, flash
from CTFd.utils.decorators import (
    admins_only,
)
from CTFd.plugins import register_plugin_assets_directory, register_admin_plugin_menu_bar
from CTFd.plugins.deployer.utils import *
from CTFd.plugins.deployer.models import DeployerChallenge, DeployerInstance
from CTFd.utils import get_config, set_config
from CTFd.utils.challenges import get_all_challenges
from CTFd.models import db, Challenges
from CTFd.utils.decorators import (
    during_ctf_time_only
)
from CTFd.utils.user import (
    authed,
    get_current_user
)
from sqlalchemy.orm import relationship
import time

# Inject deployer references into challenges to display on frontend
Challenges.deployer = relationship(
    "DeployerChallenge",
    back_populates="challenge",
    uselist=False,
    primaryjoin="Challenges.id == foreign(DeployerChallenge.chalid)"
)

import logging

plugin_blueprint = Blueprint("deployer", __name__, template_folder="assets")

@plugin_blueprint.route("/admin/deployer", methods=["GET"])
@admins_only
def deployer_instances():
    instances = list_instances()
    return render_template("deployer/dashboard.html", instances=instances)

@plugin_blueprint.route("/admin/deployer/challenges", methods=["GET"])
@admins_only
def deployer_challs():
    challenges = get_deployer_challenges()
    return render_template("deployer/challenges.html", challenges=challenges)

@plugin_blueprint.route("/admin/deployer/config", methods=["GET"])
@admins_only
def deployer_config():

    challenge_host = get_config("DEPLOYER_CHALLENGE_HOST")
    container_timeout = get_config("DEPLOYER_CONTAINER_TIMEOUT",600)
    dynamic_flags = get_config("DEPLOYER_DYNAMIC_FLAGS","No")
    flag_prefix = get_config("DEPLOYER_FLAG_PREFIX","flag")
    flag_sharing_webhook = get_config("DEPLOYER_FLAG_SHARING_WEBHOOK","")

    return render_template("deployer/config.html",
                           deployer_challenge_host=challenge_host, 
                           deployer_container_timeout=container_timeout,
                           deployer_dynamic_flags=dynamic_flags,
                           deployer_flag_prefix=flag_prefix,
                           deployer_flag_sharing_webhook=flag_sharing_webhook)

@plugin_blueprint.route("/admin/deployer/config", methods=["POST"])
@admins_only
def update_deployer_config():

    challenge_host = request.form.get("deployer_challenge_host",None)
    container_timeout = request.form.get("deployer_container_timeout",None)
    dynamic_flags = request.form.get("deployer_dynamic_flags","No")
    flag_prefix = request.form.get("deployer_flag_prefix","flag")
    flag_sharing_webhook = request.form.get("deployer_flag_sharing_webhook",None)

    if challenge_host is not None:
        set_config("DEPLOYER_CHALLENGE_HOST", challenge_host if challenge_host else "")

    if container_timeout is not None:
        try:
            container_timeout = int(container_timeout)
            set_config("DEPLOYER_CONTAINER_TIMEOUT", str(container_timeout))
        except ValueError:
            pass

    if dynamic_flags is not None:
        set_config("DEPLOYER_DYNAMIC_FLAGS", dynamic_flags)

    if flag_prefix is not None:
        set_config("DEPLOYER_FLAG_PREFIX", flag_prefix)
    
    if flag_sharing_webhook is not None:
        set_config("DEPLOYER_FLAG_SHARING_WEBHOOK", flag_sharing_webhook)

    return redirect("/admin/deployer/config")

@plugin_blueprint.route("/admin/deployer/create", methods=["GET","POST"])
@admins_only
def add_deployer_challenge():

    challenges = get_all_challenges()

    if request.form.get("nonce") is not None:

        chalid = request.form.get("chalid")
        image = request.form.get("image")
        port = request.form.get("port")
        timeout = request.form.get("timeout")

        if chalid is None or image is None or port is None or timeout is None:
            flash("All fields are required.", "danger")
            return redirect("/admin/deployer/create")
        
        exists = DeployerChallenge.query.filter_by(chalid=chalid).first()

        if exists:
            flash("This challenge is already assigned to another deployer.", "danger")
            return redirect("/admin/deployer/create")

        try:
            chal = DeployerChallenge(chalid=chalid, image=image, port=port, timeout=timeout)

            db.session.add(chal)
            db.session.commit()

            flash("Challenge created!", "success")
            return redirect("/admin/deployer/challenges")

        except:
            flash("An error occurred while saving the challenge.", "danger")
            return redirect("/admin/deployer/create")

    return render_template("deployer/create.html", challenges=challenges, deployer_container_timeout=get_config("DEPLOYER_CONTAINER_TIMEOUT"))

@plugin_blueprint.route("/admin/deployer/challenge/<int:deployer_id>", methods=["GET","POST"])
@admins_only
def edit_deployer_challenge(deployer_id):
    deployer = DeployerChallenge.query.get(deployer_id)
    challenges = get_all_challenges()

    if not deployer:
        flash("Challenge not found.", "danger")
        return redirect("/admin/deployer/challenges")
    
    if request.form.get("nonce") is not None:

        chalid = request.form.get("chalid")
        image = request.form.get("image")
        port = request.form.get("port")
        timeout = request.form.get("timeout")

        if chalid is None or image is None or port is None or timeout is None:
            flash("All fields are required.", "danger")
            return redirect("/admin/deployer/challenge/%d" % deployer_id)
        
        exists = DeployerChallenge.query.filter_by(chalid=chalid).first()

        if exists and exists.id != deployer_id:
            flash("This challenge is already assigned to another deployer.", "danger")
            return redirect("/admin/deployer/challenge/%d" % deployer_id)

        try:
        
            deployer.chalid = chalid
            deployer.image = image
            deployer.port = port
            deployer.timeout = timeout

            db.session.commit()

            flash("Challenge updated.", "success")
            return redirect("/admin/deployer/challenge/%d" % deployer_id)

        except:

            flash("An error occurred while saving the challenge.", "danger")
            return redirect("/admin/deployer/challenge/%d" % deployer_id)

    return render_template("deployer/edit.html", deployer=deployer, challenges=challenges)


@plugin_blueprint.route("/api/v1/deployer/<int:challenge_id>", methods=["GET"])
@during_ctf_time_only
def get_deployer(challenge_id):

    challenge = Challenges.query.get(challenge_id)

    if challenge is None:
        return {"error":"Challenge not found."}
    
    # There is a deployer associated with this challenge
    if challenge.deployer is not None:

        # Check if player has an instance
        user = get_current_user()
        instance = DeployerInstance.query.filter(DeployerInstance.expires >= int(time.time())).filter_by(dcid=challenge.deployer.id, playerid=user.id).first()

        return {"view":render_template("deployer/deployer_element.html", instance=instance,challenge=challenge)}

    return {"error":"There is no deployer associated with this challenge."}

@plugin_blueprint.route("/admin/deployer/stop/<string:container_id>", methods=["GET"])
@admins_only
def stop_deployer_container(container_id):

    instance = DeployerInstance.query.filter_by(container=container_id).first()

    if not instance:
        flash("Instance not found.", "danger")
        return redirect("/admin/deployer")

    try:

        kill_container(container_id)

        instance.expires = int(time.time())-1
        db.session.commit()

        flash("Instance stopped.", "success")
        return redirect("/admin/deployer")

    except:

        flash("An error occurred while stopping the instance.", "danger")
        return redirect("/admin/deployer")

@plugin_blueprint.route("/api/v1/deployer/start", methods=["POST"])
@during_ctf_time_only
def launch_deployer():
    
    challenge_id = request.form.get("challenge_id",0)

    challenge = Challenges.query.get(challenge_id)

    if challenge is None:
        return {"error":"Challenge not found."}
    
    # There is a deployer associated with this challenge
    if challenge.deployer is not None:

        # Check if player has an instance
        user = get_current_user()

        # Kill existing instances for this player
        #kill_all_by_player(user.id)

        return launch_instance(user.id,challenge_id)
        
    return {"error":"There is no deployer associated with this challenge"}


@plugin_blueprint.route("/api/v1/deployer/stop", methods=["POST"])
@during_ctf_time_only
def stop_deployer():
    
    challenge_id = request.form.get("challenge_id",0)

    challenge = Challenges.query.get(challenge_id)

    if challenge is None:
        return {"error":"Challenge not found."}
    
    # There is a deployer associated with this challenge
    if challenge.deployer is not None:

        # Check if player has an instance
        user = get_current_user()

        # Kill this instance
        response = kill_player_container(user.id,challenge_id)

        #Update expiration time to now - 1 second.
        instance = DeployerInstance.query.filter(DeployerInstance.expires >= int(time.time())).filter_by(dcid=challenge.deployer.id,playerid=user.id).first()
        instance.expires = int(time.time() -1)
        db.session.commit()

        if response:
            return response
        else:
            return {"error":"There was an error stopping this instance."}
        
    return {"error":"There is no deployer associated with this challenge"}

def load(app):
    app.db.create_all()
    app.register_blueprint(plugin_blueprint)
    register_plugin_assets_directory(app, base_path="/plugins/deployer/assets/")
    register_admin_plugin_menu_bar('Deployer', '/admin/deployer')