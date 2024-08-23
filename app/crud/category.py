from app.model.models import Category
from app.config.database import category_db,product_db,order_db,cart_db
from app.schemas.schemas import list_category,category_serial
from bson import ObjectId
from datetime import datetime
from typing import Optional

def get_category(category_id):
    query = {'_id':ObjectId(category_id),'status':'active'}
    
    try:
        category = category_serial(category_db.find_one(query))
    except:
        category = None
    return category

def get_category_name(name):
    query = {'name':name,'status':'active'}
    try:
        category = category_serial(category_db.find_one(query))
        return category
    except:
        return None
    
def get_all_category(flag:Optional[str] = None):
    try:
        if flag is not None:
            return list_category(category_db.find({'status':'active'}))
        else:
            categories = list_category(category_db.find({'status':'active'}))
            for category in categories:
                if product_db.find_one({'cat_id':category['id'],'status':'active'}) is None:
                    categories.remove(category)
            return categories
    except:
        return None
def get_random_4_category():
    try:
        categories =  list_category(category_db.aggregate([
            {'$match':{'status':'active','name':{'$ne':'electronics'}}},
            {'$sample':{'size':4}}
            ]))
        for category in categories:
            if product_db.find_one({'cat_id':category['id']}) is None:
                categories.remove(category)
        if len(categories) < 4:
            return get_random_4_category()
        return categories
    except:
        return None

def add_new_category(category: Category):
    ack = category_db.insert_one(dict(category)) 
    if ack.acknowledged:
        return True
    else:
        return False

def update_category(category: Category,category_id):
    query = {'_id':ObjectId(category_id)}
    category_db.find_one_and_update(query,dict(category))
    
def del_category(category_id):
    category =get_category(category_id)
    if category['name'] == 'electronics':
        return False
    query = {'_id':ObjectId(category_id)}
    setdata = {'$set':{'status':'inactive'}}
    category_db.update_one(query,setdata)
    # cart_db.update_many({'cat_id':category_id},{'$set':{'status':'inactive'}})
    # product_db.update_many({'cat_id':category_id},{'$set':{'status':'inactive'}})
    # order_db.update_many({'cat_id':category_id},{'$set':{'status':'inactive'}})
    move_product_to_new_category(category_id)
    
def restore_category(category_id):
    query = {'_id':ObjectId(category_id)}
    setdata = {'$set':{'status':'active'}}
    category_db.update_one(query,setdata)
    product_db.update_many({'cat_id':category_id},{'$set':{'status':'active'}})
    order_db.update_many({'cat_id':category_id},{'$set':{'status':'active'}})

def search_category(name):
    query = {'name':{'$regex':name,'$options':'i'},'status': 'active'}
    try:
        return list_category(category_db.find(query))
    except:
        return None

def update_category(category: Category, category_id: str) -> bool:
    category_data = category.dict()
    find_category = category_serial(category_db.find_one({'name': category_data['name']}))
    
    if find_category is not None:
        if str(find_category['id']) != category_id:
            return False
    query = {'_id': ObjectId(category_id)}
    set_data = {'$set': category_data}
    category_db.update_one(query, set_data)
    return True

def move_product_to_new_category(old_cat_id):
    new_cat = get_category_name('electronics')
    if new_cat is None:
        new_cat = Category(name='electronics',status='active',description='All electronics products',image='https://t4.ftcdn.net/jpg/03/64/41/07/360_F_364410756_Ev3WoDfNyxO9c9n4tYIsU5YBQWAP3UF8.jpg',last_change=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        add_new_category(dict(new_cat))
        move_product_to_new_category(old_cat_id)
    query = {'cat_id':old_cat_id}
    setdata = {'$set':{'cat_id':new_cat['id']}}
    product_db.update_many(query,setdata)