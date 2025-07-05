from CTFd.models import db

class DeployerChallenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chalid = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    image = db.Column(db.String(255))
    port = db.Column(db.Integer)
    timeout = db.Column(db.Integer)
    challenge = db.relationship("Challenges", back_populates="deployer", lazy="joined")

    def __init__(self, chalid, image,port,timeout):
        self.chalid = chalid
        self.image = image
        self.port = port
        self.timeout = timeout

    def __repr__(self):
        return '<deployable {}, {}, {}, {}>'.format(self.chalid, self.image, self.port, self.timeout)
    

class DeployerInstance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dcid = db.Column(db.Integer, db.ForeignKey('deployer_challenge.id'))
    playerid = db.Column(db.Integer, db.ForeignKey('users.id'))
    expires = db.Column(db.Integer)
    fqdn = db.Column(db.String(255))
    container = db.Column(db.String(12))
    deployer = db.relationship("DeployerChallenge", backref="instance", lazy="joined")
    player = db.relationship("Users", backref="instance", lazy="joined")

    def __init__(self, dcid, playerid, expires, fqdn, container):
        self.dcid = dcid
        self.playerid = playerid
        self.expires = expires
        self.fqdn = fqdn
        self.container = container

    def __repr__(self):
        return '<instance {}, {}, {}, {}, {}>'.format(self.dcid, self.playerid, self.expires, self.fqdn, self.container)