# CTFd-Ployer Plugin

A CTFd plugin for deploying per-player instanced challenges using the [CTFd-Ployer system](https://github.com/jselliott/CTFd-ployer). To use this plugin:

* Clone this repository into your CTFd plugins folder:

```
git clone https://github.com/jselliott/CTFd-ployer-Plugin deployer
```

* Replace the default flags plugin *__init__.py* with the one in this repo to add support for dynamic flags (optionally back up the original file)

```
cd deployer
mv ../flags/__init__.py ../flags/__init__.py.bak
cp flags/__init__.py ../flags/__init__.py
```

* Restart CTFd
* Browse to the admin area in CTFd and put in the URL for your challenge deployer host, add challenge container details, etc.
* Enjoy!


