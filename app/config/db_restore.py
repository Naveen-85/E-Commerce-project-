from fastapi import APIRouter
from app.config.database import *
from datetime import datetime
import json
from app.config.cypher import hash_password
import requests
import base64

router = APIRouter()


def clear_db():
    user_db.delete_many({})
    product_db.delete_many({})
    category_db.delete_many({})
    seller_db.delete_many({})
    order_db.delete_many({})
    cart_db.delete_many({})

def image_to_base64(image_data):
    encoded_data = []
    for image in image_data:
        response = requests.get(image)
        if response.status_code == 200:
            raw_data = response.content
            base64_encoded = base64.b64encode(raw_data).decode('utf-8')
            encoded_data.append(base64_encoded)
    return encoded_data

def new_category():
    with open("app/data/category.json", "r") as file:
        categories = json.load(file)
        for category in categories:
            category['last_change'] = datetime.now()
            category_db.insert_one(category)
            
def new_product():
    seller_data = seller_db.find()
    seller_data = {seller['name']:str(seller['_id']) for seller in seller_data}
    category_data = category_db.find()
    category_data = {category['name']:str(category['_id']) for category in category_data}
    with open("app/data/product.json", "r") as file:
        products = json.load(file)
        for product in products:
            product['images'] = image_to_base64(product['images'])
            product['seller_id'] = seller_data.get(product['seller_id'])
            product['cat_id'] = category_data.get(product['cat_id'])
            product['last_change'] = datetime.now()
            product_db.insert_one(product)

def new_seller():
    with open("app/data/sellers.json", "r") as file:
        sellers = json.load(file)
        for seller in sellers:
            seller['password'] = hash_password(seller['password'])
            seller['last_login'] = None
            seller_db.insert_one(seller)

def new_user():
    with open("app/data/users.json", "r") as file:
        users = json.load(file)
        for user in users:
            user['password'] = hash_password(user['password'])
            user['last_login'] = None
            user_db.insert_one(user)



@router.get("/restore")
def restore_db():
    clear_db()
    new_category()
    new_seller()
    new_product()
    new_user()
    return {"message": "Restore database"}


