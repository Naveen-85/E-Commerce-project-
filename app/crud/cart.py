from app.model.models import Cart
from app.config.database import cart_db, order_db
from app.schemas.schemas import cart_serial, list_cart
from bson import ObjectId
from app.crud.product import get_product, update_product_stock
from datetime import datetime


def get_cart_user(user_id):
    query = {'user_id':user_id}
    try:
        return cart_serial(cart_db.find_one(query))
    except:
        return None

        
def add_cart_product(user_id, product_id, quantity):
    cart = cart_db.find_one({'user_id':user_id})
    last_change = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    if cart == None:
        last_change = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        product = get_product(product_id)
        total_price = str(int(product['price']) * quantity)
        cart = Cart(user_id=user_id, product_data={product_id:quantity}, total_price=total_price, last_change=last_change)
        ack = cart_db.insert_one(cart.dict())
        
    else:
        cart = cart_serial(cart)
        if product_id in cart['product_data'].keys():
            
            cart['product_data'][product_id] += quantity
        else:
            cart['product_data'][product_id] = quantity 
        cart['last_change'] = last_change
        cart['total_price'] = str(int(cart['total_price']) + int(get_product(product_id)['price']) * quantity)   
        ack = cart_db.update_one({'user_id':user_id}, {'$set': {'product_data':cart['product_data'], 'last_change':cart['last_change'], 'total_price':cart['total_price']}})
    if ack.acknowledged:
        return True
    else:
        return False

def update_cart_product(user_id, product_id, flag):
    cart = cart_serial(cart_db.find_one({'user_id':user_id}))
    if product_id in cart['product_data'].keys():
        if flag:
            product = get_product(product_id)
            if product['stock'] <= cart['product_data'][product_id]:
                return False
            cart['product_data'][product_id] += 1
        else:
            cart['product_data'][product_id] -= 1
            
        cart['total_price'] = str(int(cart['total_price']) + int(get_product(product_id)['price']) * (1 if flag else -1))
        ack = cart_db.update_one({'user_id':user_id}, {'$set': {'product_data':cart['product_data'], 'total_price':cart['total_price']}})
        if ack.acknowledged:
            return True
    


def remove_cart_product(user_id, product_id):
    cart = cart_db.find_one({'user_id':user_id})
    cart = cart_serial(cart)
    if product_id in cart['product_data'].keys():
        cart['total_price'] = str(int(cart['total_price']) - int(get_product(product_id)['price']) * cart['product_data'][product_id])
        del cart['product_data'][product_id]
        ack = cart_db.update_one({'user_id':user_id}, {'$set': {'product_data':cart['product_data'], 'total_price':cart['total_price']}})
        if ack.acknowledged:
            return True
    return False

def check_product_status(product_id, quantity):
    product = get_product(product_id)
    if product == None:
        return {'message':'The Product not Available', 'response':False}
    elif product['stock'] < quantity and product['stock'] != 0:
        return {'message':'There is Insufficient Stock', 'response':False,'product_id':product_id}
    elif product['stock'] == 0:
        return {'message':'The Product is Out of Stock', 'response':False} 
    return {'message':'The Product is Available', 'response':True}


def cart_price_update(cart_id):
    cart = cart_serial(cart_db.find_one({'_id':ObjectId(cart_id)}))
    total_price = 0
    remove_prod_id = set()
    for product_id, qty in cart['product_data'].items():
        product = get_product(product_id)
        if product == None or product['stock'] < qty or product['stock'] == 0:
            remove_prod_id.add(product_id)
            continue
        total_price += int(product['price']) * qty
    for product_id in remove_prod_id:
        del cart['product_data'][product_id]
    ack = cart_db.update_one({'_id':ObjectId(cart_id)}, {'$set': {'total_price':str(total_price),'last_change':datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 'product_data':cart['product_data']}})
    if ack.acknowledged:
        return True
    return False

def checkout_cart(user_id):
    cart = cart_serial(cart_db.find_one({'user_id':user_id}))
    order = {'user_id':user_id, 'product_data':cart['product_data'], 'total_price':cart['total_price'], 'order_date':datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 'last_change':datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 'status':'active'}
    for product_id, qty in cart['product_data'].items():
        response = check_product_status(product_id, qty)
        if response['response'] == False:
            cart_price_update(cart['id'])
            return {'message':'Error', 'response':response['message']}
        product = get_product(product_id)
        update_product_stock(product_id, product['stock'] - qty)
    ack = order_db.insert_one(order)
    if ack.acknowledged:
        cart_db.delete_one({'user_id':user_id})
        return {'order_id':str(ack.inserted_id),'message':'True'}
    return {'message':'False'}

