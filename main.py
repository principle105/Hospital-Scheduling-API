from flask import Flask
from threading import Thread
from flask_restful import Resource, Api
import string
import random
import os
import pymongo
import dns
import ast
import bcrypt

cluster = pymongo.MongoClient(os.getenv("db-token"))
db = cluster["design"]
collection = db["users"]
hcollection = db["hospitals"]

app = Flask("")
api = Api(app)

def add_stat(collection_name,theid,stat,value):
  col = db[collection_name]
  col.update_one({"_id": theid}, {"$push": {stat: value}})

def update_stat(collection_name,theid,stat,value):
  col = db[collection_name]
  col.update_one({"_id": theid}, {"$set": {stat: value}})

def hash_password(p):
  p = p.encode("utf-8")
  salt = bcrypt.gensalt()
  hashed = bcrypt.hashpw(p,salt)
  return hashed.decode("utf-8")

class GetUser(Resource):
  def get(self, username):
    try:
      results = collection.find_one({"_id": username})
      if results is None:
        return {"message": "That user does not exist"}
      else:
        return results
    except Exception as e:
      return {"message": e}

class DeleteUser(Resource):
  def post(self, username):
    try:
      collection.delete_one({"_id": username}) 
    except:
      pass
  
class RegisterUser(Resource):
  def get(self, username, password):
    try:
      results = collection.find_one({"_id": username})
      if results is None:
        post = {"_id": username, "p": hash_password(password), "h": []}
        collection.insert_one(post)
        return post
      else:
        return {"message": "That is already a registered user"} 
    except Exception as e:
      return {"message": e}

class CreateHospital(Resource):
  def get(self,name,creator_username):
    try:
      results = hcollection.find_one({"_id": name})
      if results is None:
        post = {"_id": name,"join": ("".join(random.choice(string.ascii_letters) for i in range(10))), "can_change": True, "can_join": True,"u": {creator_username:{"r": 1, "s": [[0]*8]*7,"u": creator_username}}}
        hcollection.insert_one(post)
        add_stat("users",creator_username,"h",name)
        return collection.find_one({"_id": creator_username})
      else:
        return {"message": "That is an existing hospital"} 
    except Exception as e:
      print(e)
      return {"message": e}

class JoinHospital(Resource):
  def get(self,name,join_code,creator_username):
    try:
      results = hcollection.find_one({"_id": name})
      if results is not None:
        if results["can_join"] == False:
          return {"message": "This hospital has restricted new members from joining"}
        if results["join"] == join_code:
          results["u"][creator_username] = {"r": 0, "s": [[0]*8]*7,"u": creator_username}
          hcollection.update_one({"_id": name}, {"$set": {"u": results["u"]}})
          add_stat("users",creator_username,"h",name)
          return collection.find_one({"_id": creator_username})
        else:
          return {"message": "Invalid join code"}
      else:
        return {"message": "Invalid hospital name"}
    except Exception as e:
      print(e)
      return {"message": e}

class GetHospital(Resource):
  def get(self,name):
    try:
      results = hcollection.find_one({"_id": name})
      if results is None:
        return {"message": "That hospital does not exist"}
      else:
        return results
    except Exception as e:
      print(e)
      return {"message": e}

class UpdateSchedule(Resource):
  def get(self,hospital,username,value):
    value = ast.literal_eval(value) 
    results = hcollection.find_one({"_id": hospital})
    if results is not None:
      if results["can_change"] == False:
        return {"message": "This hospital has restricted members from updating their schedules"}
      results["u"][username]["s"] = value
      hcollection.update_one({"_id": hospital}, {"$set": {"u": results["u"]}})
      return {"message": "Stat successfully updated"}
    else:
      return {"message": "Invalid username"}

class UpdateHospital(Resource):
  def get(self,hospital,stat,value):
    try:
      value = ast.literal_eval(value)
    except:
      pass
    results = hcollection.find_one({"_id": hospital})
    if results is not None:
      hcollection.update_one({"_id": hospital}, {"$set": {stat: value}})
      return {"message": "Succesfully Updated"}
    else:
      return {"message": "Invalid hospital name"}

api.add_resource(GetUser, "/user/get_user/<string:username>")
api.add_resource(DeleteUser, "/user/delete_user/<string:username>")
api.add_resource(RegisterUser, "/user/register_user/<string:username>/<string:password>")

api.add_resource(CreateHospital, "/hospital/create_hospital/<string:name>/<string:creator_username>")
api.add_resource(JoinHospital, "/hospital/join_hospital/<string:name>/<string:join_code>/<string:creator_username>")
api.add_resource(GetHospital, "/hospital/get_hospital/<string:name>")
api.add_resource(UpdateSchedule, "/hospital/update_schedule/<string:hospital>/<string:username>/<string:value>")
api.add_resource(UpdateHospital, "/hospital/update_hospital/<string:hospital>/<string:stat>/<string:value>")

def run():
  app.run(host="0.0.0.0",port=8080)

t = Thread(target=run)
t.start()   