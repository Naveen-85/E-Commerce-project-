from app.model.models import Product
from app.config.database import product_db, category_db,order_db,cart_db
from app.schemas.schemas import list_product, product_serial, category_serial
from bson import ObjectId

def get_product(product_id):
    query = {'_id':ObjectId(product_id),'status':'active'}
    try:
        product = product_serial(product_db.find_one(query))
    except:
        product = None
    return product

def get_product_name(name):
    query = {'name':name,'status':'active'}
    try:
        return product_serial(product_db.find_one(query))
    except:
        return None
    
def get_all_product():
    try:
        return list_product(product_db.find({'status':'active'}))
    except:
        return None
    
def get_product_cat(cat_id):
    query = {'cat_id':cat_id,'status':'active'}
    try:
        return list_product(product_db.find(query))
    except:
        return None
    
def get_product_sell(seller_id):
    query = {'seller_id':seller_id,'status':'active'}
    try:
        return list_product(product_db.find(query))
    except:
        return None

def get_random_product():
    try:
        return list_product(product_db.aggregate([{'$match': {'status': 'active'}},{'$sample':{'size':12}}]))
    except:
        return None

def get_random_product1():
    try:
        return product_serial(product_db.aggregate([{'$match': {'status': 'active'}},{'$sample':{'size':1}}]))
    except:
        return None

def add_new_product(product: Product):
    ack = product_db.insert_one(dict(product)) 
    if ack.acknowledged:
        return True
    else:
        return False

def update_product(product: Product,product_id):
    query = {'_id':ObjectId(product_id)}
    filter = {'$set':dict(product)}
    ack = product_db.update_one(query,filter)
    if ack.acknowledged:
        return True
    else:
        return False
    
def update_product_stock(product_id,stock):
    query = {'_id':ObjectId(product_id)}
    filter = {'$set':{'stock':stock}}
    ack = product_db.update_one(query,filter)
    if ack:
        return True
    else:
        return False
    
def del_product(product_id):
    query = {'_id':ObjectId(product_id)}
    setdata = {'$set':{'status':'inactive'}}
    ack = product_db.update_one(query,setdata)
    query = {f'product_data.{product_id}': {'$exists': True}}
    order_db.update_many(query,{'$set':{'status':'inactive'}})
    cart_db.update_many(query,{'$set':{'status':'inactive'}})
    
    if ack.acknowledged:
        return True
    else:
        return False

def search_product(query:str):
    try:
        products = product_db.find({'name':{'$regex':query,"$options": "i"},'status':'active'})
        return list_product(products)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_product_by_cat_id_sort(cat_id, sort_order):
    query = {'cat_id': cat_id, 'status': 'active'}
    try:
        # Retrieve the products from the database
        products = list(product_db.find(query))
        
        # Convert price from string to float and sort manually
        products.sort(key=lambda x: (
            float(x['price'])            # Then, sort by price
        ), reverse=(sort_order == -1))
        
        products = [product for product in products if product['stock'] != 0 ] + [0]*products.count(0) + [product for product in products if product['stock'] == 0 ]
        return list_product(products)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
def search_product_by_name_seller_id(seller_id,name):
    query = {'seller_id':seller_id,'name':{'$regex':name,"$options": "i"},'status':'active'}
    try:
        products = product_db.find(query)
        return list_product(products)
    except:
        return None
    
def get_recommended_products(category_id: str, current_product_id: str):
    all_products = get_product_cat(category_id)
    recommended_products = [prod for prod in all_products if prod['id'] != current_product_id]
    if recommended_products == []:
        default_category = category_serial(category_db.find_one({'name': 'laptop'}))
        all_products = get_product_cat(default_category['id'])
        recommended_products = all_products
    return recommended_products[:4] 


