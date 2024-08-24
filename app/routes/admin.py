from fastapi import APIRouter,Request,Form,Query,HTTPException
from fastapi.responses import HTMLResponse,RedirectResponse
from app.model.models import Admin, Category, Product, User, Order, Seller
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from app.crud.admin import get_admin_username, update_admin
from app.crud.category import add_new_category, get_all_category, get_category, del_category, restore_category,search_category,update_category, get_category_name
from app.crud.product import get_all_product,del_product,get_product,search_product
from app.crud.user import get_all_user, get_user, del_user,search_users_by_name
from app.crud.seller import get_all_seller, get_seller_mail, add_seller, del_seller,get_seller,search_seller
from app.crud.order import get_all_order, del_order
from app.config.session import login_admin, get_current_admin,logout_admin
from app.config.cypher import verify_password,hash_password
import datetime
from app.config.database import category_db
from app.schemas.schemas import category_serial


router = APIRouter()
templates =  Jinja2Templates(directory='app/templates')

@router.get('/admin_login',response_class= HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("admin_login.html",{'request':request})

@router.post('/admin_login',response_class=HTMLResponse)
def login(request: Request, username:str = Form(...), password:str = Form(...)):
    admin = get_admin_username(username)
    if admin != None and verify_password(admin['password'],password):
        login_admin(request,str(admin['username']))
        return RedirectResponse(url='/admin_dashboard',status_code=302)
    return templates.TemplateResponse('admin_login.html',{'request':request,"error":"invalid username or password"})

@router.get('/admin_dashboard',response_class=HTMLResponse)
def dashboard(request: Request):
    admin = get_current_admin(request)
    if admin == None:
        return RedirectResponse(url='/admin_login',status_code=302)
    return templates.TemplateResponse('admin_dashboard.html',{'request':request,'admin':admin})

@router.get('/admin_logout',response_class=HTMLResponse)
def logout(request: Request):
    logout_admin(request)
    return RedirectResponse(url='/admin_login',status_code=302)

@router.get('/add_category',response_class=HTMLResponse)
def category_page(request:Request):
    admin=get_current_admin(request)
    return templates.TemplateResponse('add_category.html',{'request':request,"admin":admin})

@router.post('/add_category',response_class=HTMLResponse)
def add_category_new(request: Request, name:str = Form(...), description:str = Form(...), image:str = Form(...)):
    admin=get_current_admin(request)
    exist_cat = get_category_name(name.lower())
    if exist_cat != None:
        return templates.TemplateResponse("add_category.html", {"request": request,"admin":admin,"message":"Category Already exist"})
    category = Category(name=name.lower(),description=description,image=image,last_change=str(datetime.datetime.now()))
    ack = add_new_category(category)
    if ack:
        return RedirectResponse(url='/manage_category',status_code=302)
    else:
        return templates.TemplateResponse("add_category.html", {"request": request,"admin":admin,"message":"Something went wrong"})
    

@router.get('/manage_user',response_class=HTMLResponse)
def manage_user(request: Request):
    admin = get_current_admin(request)
    users = get_all_user()
    return templates.TemplateResponse('manage_user.html',{'request':request,"admin":admin,"users":users})

@router.get('/del_user/{user_id}',response_class=HTMLResponse)
def delete_user_data(request:Request,user_id:str):
    admin=get_current_admin(request)
    del_user(user_id)
    return RedirectResponse(url="/manage_user")
                            
                            

@router.get('/order_logs',response_class=HTMLResponse)
def order_logs(request: Request):
    admin = get_current_admin(request)
    orders_data = get_all_order()
    orders = []
    for item in orders_data:
        order = {}
        user_data = get_user(item['user_id'])
        for product_id, quantity in item['product_data'].items():
            product = get_product(product_id)
            if product is None:
                continue
            seller = get_seller(product['seller_id'])
            if seller is None:
                continue
            order['id'] = item['id']
            order['seller'] = seller['name']
            order['product'] = product['name']
            order['quantity'] = quantity
            order['user'] = user_data['name']
            order['category'] = get_category(product['cat_id'])['name']
            order['price'] = int(product['price']) * quantity
            orders.append(order)
        
    return templates.TemplateResponse('manage_order.html',{'request':request,"admin":admin,"orders":orders})

@router.get('/delete_order/{order_id}',response_class=HTMLResponse)
def delete_order_data(request:Request,order_id:str):
    admin=get_current_admin(request)
    del_order(order_id)
    return RedirectResponse(url="/order_logs")


@router.get('/manage_category',response_class=HTMLResponse)
def manage_category(request: Request):
    admin = get_current_admin(request)
    categories = get_all_category(flag=True)
    return templates.TemplateResponse('manage_category.html',{'request':request,"admin":admin,"categories":categories})

@router.get('/manage_category_del/{item_id}',response_class=HTMLResponse)
def del_category_item(request:Request,item_id:str):
    admin=get_current_admin(request)
    del_category(item_id)
    return RedirectResponse(url="/manage_category" )

@router.get('/restore_category/{item_id}',response_class=HTMLResponse)
def restore_category_item(request:Request,item_id:str):
    admin=get_current_admin(request)
    restore_category(item_id)
    return RedirectResponse(url="/manage_category" )

@router.get('/manage_product',response_class=HTMLResponse)
def manage_product(request: Request):
    admin = get_current_admin(request)
    products = get_all_product()
    categories = get_all_category()
    categories = {category['id']:category['name'] for category in categories}
    
    seller = get_all_seller()
    seller = {seller['id']:seller['name'] for seller in seller}
    data = []
    for product in products:
        temp = {}
        temp['id']=product['id']
        temp['product'] = product['name']
        temp['category'] = categories[product['cat_id']]
        temp['price'] = product['price']
        temp['seller'] = seller[product['seller_id']]
        temp['quantity'] = product['stock']
        data.append(temp)
    return templates.TemplateResponse('manage_product.html',{'request':request,"admin":admin,"data":data})

@router.get('/manage_seller',response_class=HTMLResponse)
def manage_seller(request: Request):
    admin = get_current_admin(request)
    sellers = get_all_seller()
    return templates.TemplateResponse('manage_seller.html',{'request':request,"admin":admin,"sellers":sellers})

@router.get('/manage_product_del/{item_id}',response_class=HTMLResponse)
def del_product_item(request:Request,item_id:str):
    admin=get_current_admin(request)
    del_product(item_id)
    return RedirectResponse(url="/manage_product",status_code=302)

@router.get('/add_seller',response_class=HTMLResponse)
def seller_register(request: Request):
    admin = get_current_admin(request)
    return templates.TemplateResponse('add_seller.html',{'request':request,"admin":admin})

@router.post('/add_seller',response_class=HTMLResponse)
def seller_register(request: Request, name:str = Form(...), email: str=Form(...), password: str=Form(...), number: int=Form(...)): 
    admin = get_current_admin(request)
    if len(str(number)) != 10:
        return templates.TemplateResponse("add_seller.html", {"request": request,"admin":admin,"message":"Invalid phone number"})
    item = get_seller_mail(email.lower())
    if item != None:
        return templates.TemplateResponse("add_seller.html", {"request": request,"admin":admin,"message":"Seller Already exist"})
    else:
        password = hash_password(password)
        seller = Seller(name=name,email=email.lower(),password=password,phone=number,status='active')
        ack = add_seller(seller)
        if ack:
          return templates.TemplateResponse("add_seller.html", {"request": request,"admin":admin,"success":"Seller registered successfully"})
        else:
            return templates.TemplateResponse("add_seller.html", {"request": request,"admin":admin,"message":"Something went wrong"})

@router.get('/delete_seller/{seller_id}',response_class=HTMLResponse)
def delete_seller(request:Request,seller_id:str):
    admin=get_current_admin(request)
    del_seller(seller_id)
    return RedirectResponse(url="/manage_seller",status_code=302)


@router.get('/search_user',response_class=HTMLResponse)
def search_user(request: Request, query: str = Query(...)):
    admin = get_current_admin(request)
    users = search_users_by_name(query)
    
    if not users:
        users = []
        message = "No users found"
    else:
        message = ""
    
    return templates.TemplateResponse('manage_user.html', {
        'request': request, 
        "admin": admin, 
        "users": users, 
        "message": message
    })
    

@router.get('/search_category_name',response_class=HTMLResponse)
def search_category_name(request: Request, query: str = Query(...)):
    admin = get_current_admin(request)
    categories = search_category(query)
    
    if not categories:
        message = "No categories found"
    else:
        message = ""
    
    return templates.TemplateResponse('manage_category.html', {
        'request': request, 
        'admin': admin, 
        'categories': categories, 
        'message': message
    })

@router.get('/search_seller_name',response_class=HTMLResponse)
def search_seller_name(request:Request,query:str=Query(...)):
    admin=get_current_admin(request)
    sellers=search_seller(query)
    return templates.TemplateResponse('manage_seller.html',{'request':request,'admin':admin,'sellers':sellers})

    
    return templates.TemplateResponse('manage_product.html',{'request':request,"admin":admin,"data":data})
@router.get('/order_logs',response_class=HTMLResponse)
def order_logs(request: Request):
    admin = get_current_admin(request)
    orders_data = get_all_order()
    orders = []
    for item in orders_data:
        order = {}
        user_data = get_user(item['user_id'])
        for product_id, quantity in item['product_data'].items():
            product = get_product(product_id)
            seller = get_seller(product['seller_id'])
            order['id'] = item['id']
            order['seller'] = seller['name']
            order['product'] = product['name']
            order['quantity'] = quantity
            order['user'] = user_data['name']
            order['category'] = get_category(product['cat_id'])['name']
            order['price'] = int(product['price']) * quantity
            orders.append(order)
        
    return templates.TemplateResponse('manage_order.html',{'request':request,"admin":admin,"orders":orders})
@router.get('/search_product_name', response_class=HTMLResponse)
def search_product_name(request: Request, query: str = Query(...)):
    admin = get_current_admin(request)
    products = search_product(query)
    
    if not products:
        return templates.TemplateResponse('manage_product.html', {'request': request, "admin": admin, "data": [], "message": "No product found"})
    
    categories = get_all_category()
    categories = {category['id']: category['name'] for category in categories}
    
    sellers = get_all_seller()
    sellers = {seller['id']: seller['name'] for seller in sellers}
    
    data = []
    for product in products:
        temp = {
            'id': product['id'],
            'product': product['name'],
            'category': categories.get(product['cat_id'], 'Unknown'),
            'price': product['price'],
            'seller': sellers.get(product['seller_id'], 'Unknown'),
            'quantity': product['stock']
        }
        data.append(temp)
    
    return templates.TemplateResponse('manage_product.html', {'request': request, "admin": admin, "data": data})
    
@router.get("/manage_category_edit/{category_id}", response_class=HTMLResponse)
def edit_category_page(request: Request, category_id: str):
    category = get_category(category_id)
    admin = get_current_admin(request)
    return templates.TemplateResponse("edit_category.html", {"request": request, "category": category, "admin": admin})

@router.post('/category_edit/', response_class=HTMLResponse)
def category_update(request: Request, category_id: str = Form(...), name: str = Form(...), description: str = Form(...), image:str= Form(...)):
    admin  = get_current_admin(request)
    category_data=get_category(category_id)
    if category_data is None:
        return templates.TemplateResponse("500.html", {"request": request, "error": "Category not found"})
    
    category = Category(name=name, description=description, image=image, last_change=str(datetime.datetime.now()), status='active')
    ack = update_category(category, category_id)
    
    if not ack:
        return templates.TemplateResponse("edit_category.html", {"request": request,"admin":admin ,"error": "Category name already exists", "category": category_data})
    elif ack:
        admin = get_current_admin(request)
        categories = get_all_category()
        return templates.TemplateResponse('manage_category.html',{'request':request,"admin":admin,"categories":categories})

    else:
        return templates.TemplateResponse("500.html", {"request": request})
@router.get("/admin_forgot_password",response_class=HTMLResponse)
def admin_forgot_password(request:Request):
    return templates.TemplateResponse("admin_reset_password.html", {"request":request})

@router.post("/admin_reset_password", response_class=HTMLResponse)
def admin_reset_password(
    request: Request,
    username: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...)
):
    if new_password != confirm_new_password:
        return templates.TemplateResponse("admin_reset_password.html", {"request": request, "error": "New passwords do not match."})

    # Query for the admin user
    admin = get_admin_username(username)
    if not admin:
        return templates.TemplateResponse("admin_reset_password.html", {"request": request, "error": "User doesn't exist."})

    # Hash the current password
    hashed_current_password = hash_password(current_password)

    # Verify the current password
    if  verify_password(admin['password'],current_password)==False:
        return templates.TemplateResponse("admin_reset_password.html", {"request": request, "error": "Current password is incorrect."})

    # Hash the new password
    hashed_new_password = hash_password(new_password)

    # Update the admin password in the database
    if update_admin(admin["username"], hashed_new_password):
        return templates.TemplateResponse('admin_login.html',{'request':request,"success":"password updated successfully"})
        
    else:
        return templates.TemplateResponse("admin_reset_password.html", {"request": request, "error": "Error updating password."})
    