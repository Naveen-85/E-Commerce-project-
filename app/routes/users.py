from fastapi import APIRouter,Request,Form,Query,HTTPException, FastAPI, Response
from fastapi.responses import HTMLResponse,RedirectResponse,JSONResponse
from app.model.models import User, Cart
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from app.crud.user import get_user_mail,add_user, update_last_login,update_user
from app.config.session import login_user, get_current_user,logout_user,get_temp_user
from app.crud.category import get_all_category,get_category,search_category,get_random_4_category
from app.crud.product import get_product_cat, get_random_product, search_product,get_product,get_product_by_cat_id_sort,get_recommended_products
from app.crud.cart import add_cart_product, get_cart_user, remove_cart_product, update_cart_product, checkout_cart,cart_price_update
from app.crud.order import get_order_user,get_order
from datetime import datetime
from app.config.cypher import verify_password,hash_password
import re


router = APIRouter()
templates =  Jinja2Templates(directory='app/templates')

#user login and logout
@router.get('/user_login',response_class= HTMLResponse)
def login_page(request: Request, response: Response):
    logout_user(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return templates.TemplateResponse("user_login.html",{'request':request,'response':response})

@router.post('/user_login',response_class=RedirectResponse)
def login(request: Request, email:str = Form(...), password:str = Form(...)):
    user = get_user_mail(email)
    if user != None and  verify_password(user['password'],password):
        login_user(request,str(user['email']),'auth')
        update_last_login(user['id'])
        return RedirectResponse(url='/',status_code=302)
    return templates.TemplateResponse('user_login.html',{'request':request,"error":"invalid email or password"})

@router.get('/user_logout',response_class=RedirectResponse)
def user_logout(request: Request, response: Response):
    logout_user(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return RedirectResponse(url='/')

#user registration        
@router.post('/add_user', response_class=HTMLResponse)
def user_register(request: Request, name:str = Form(...), email: str=Form(...), password: str=Form(...), address: str=Form(...)): 
    item = get_user_mail(email)
    if item != None:
        return templates.TemplateResponse("user_register.html", {"request": request,"message":"User Already exist"})
    else:
        password = hash_password(password)
        user = User(name=name,password=password,email=email,address=address)
        ack = add_user(user)
        if ack:
          return templates.TemplateResponse("user_register.html", {"request": request,"success":"User registered successfully"})
        else:
            return templates.TemplateResponse("user_register.html", {"request": request,"message":"Something went wrong"})
            
@router.get('/add_user', response_class=HTMLResponse)
def user_registration(request: Request):
    return templates.TemplateResponse("user_register.html",{"request":request})

#user landing page
@router.get('/', response_class=HTMLResponse)
def landing_page(request: Request):
    user = get_current_user(request)
    categories = get_random_4_category()
    nav_categories = get_all_category()
    products = get_random_product()
    return templates.TemplateResponse("user_landing.html",{"request":request,"user":user,"categories":categories,"products":products,"nav_categories":nav_categories})
#category page
@router.get('/user_category/{cat_id}')
def cat_page(request: Request, cat_id: str):
    user = get_current_user(request)
    category = get_category(cat_id)
    if category == None:
        return RedirectResponse(url="/404")
    categories = get_all_category()
    products = get_product_cat(cat_id)
    return templates.TemplateResponse("users_category.html",{'request':request,"user":user,"category":category,"categories":categories,"products":products})
    
@router.get('/search/', response_class=HTMLResponse)
def search(request: Request, query: str):
    user = get_current_user(request)
    categories = get_all_category()
    res_products = []
    cat_product = []
    res_products = search_product(query)
    cat_list = search_category(query)
    for cat in cat_list:
        cat_product += get_product_cat(str(cat['id']))
    if res_products != None and cat_list != None:
        res_products += cat_product
    elif res_products == None and cat_list != None:
        res_products += cat_product
    unique = [i['id'] for i in res_products]
    unique = list(set(unique))
    unique_list = []
    for i in res_products:
        if i['id'] in unique:
            unique_list.append(i)
            unique.remove(i['id'])
    res_products = unique_list
    
    return templates.TemplateResponse("search_page.html",{"request":request,"user":user,"categories":categories,"products":res_products,"query":query})

#product page
@router.get('/user_product/{prod_id}', response_class=HTMLResponse)
def product_page(request: Request, prod_id: str):
    user = get_current_user(request)
    categories = get_all_category()
    product = get_product(prod_id)
    if product == None:
        return RedirectResponse(url="/404")
    recommended_products = get_recommended_products(product['cat_id'],prod_id)
    return templates.TemplateResponse("product_page.html",{"request":request,"user":user,"categories":categories,"product":product,"recommended_products":recommended_products})

@router.get('/add_to_cart', response_class=HTMLResponse)
def cart_page(request: Request, product_id: str= Query(...), quantity: int = Query(...)):
    user = get_current_user(request)
    categories = get_all_category()
    product_data = get_product(product_id)
    if product_data == None:
        return RedirectResponse(url="/404")
    if quantity > product_data['stock']:
        return JSONResponse(status_code=400, content={"success": False, "message": "Not enough stock available"})
    user_data = get_user_mail(user)
    if user_data == None:
        return RedirectResponse(url="/404")
    ack = add_cart_product(user_data['id'],product_id,quantity)
    if ack:
         return JSONResponse(status_code=200, content={"success": True, "message": "Product added to cart successfully"})
    else:
         return JSONResponse(status_code=400, content={"success": False, "message": "Something went wrong. Please try again later"}) 
     
@router.get('/buy_now', response_class=HTMLResponse)
def buy_now(request: Request, product_id: str= Query(...), quantity: int = Query(...)):
    user = get_current_user(request)
    categories = get_all_category()
    product_data = get_product(product_id)
    if product_data == None:
        return RedirectResponse(url="/404")
    if quantity > product_data['stock']:
        return JSONResponse(status_code=400, content={"success": False, "message": "Not enough stock available"})
    user_data = get_user_mail(user)
    if user_data == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    ack = add_cart_product(user_data['id'],product_id,quantity)
    if ack:
        return JSONResponse(status_code=200, content={"redirect": True, "message": "Redirecting..", "url": "/user_cart"})
    else:
        return JSONResponse(status_code=400, content={"success": False, "message": "Something went wrong. Please try again later"})


# 404_page_not_found
@router.get("/404", response_class=HTMLResponse)
async def catch_all(request: Request):
    return templates.TemplateResponse("error_page.html", {"request": request}, status_code=404)

@router.get('/user_cart',response_class=HTMLResponse)
def cart(request: Request):
    user = get_current_user(request)
    user_data = get_user_mail(user)
    if user == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    categories = get_all_category()
    cart_data = get_cart_user(user_data['id'])
    if user == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    products = []
    super_total = 0
    if cart_data != None:
        for prod_id, qty in cart_data['product_data'].items():
            temp_dict = {}
            product = get_product(prod_id)
            if product == None:
                cart_price_update(cart_data['id'])
                continue
            temp_dict['id'] = prod_id
            temp_dict['image'] = product['images'][0]
            temp_dict['name'] = product['name']
            temp_dict['description'] = product['base_feature']
            temp_dict['price'] = product['price']
            temp_dict['qty'] = qty
            temp_dict['total_price'] = str(int(product['price']) * qty)
            products.append(temp_dict)
        super_total = cart_data['total_price']
    return templates.TemplateResponse("cart.html",{"request":request,"user":user,"categories":categories,"products":products,"super_total":super_total})


@router.delete('/remove_cart_item', response_class=RedirectResponse)
def remove_cart_item(request: Request, product_id: str = Query(...)):
    user = get_current_user(request)
    user_data = get_user_mail(user)
    if user_data == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    ack = remove_cart_product(user_data['id'],product_id)
    if ack:
        return RedirectResponse(url='/user_cart')
    return RedirectResponse(url='/404')

@router.get('/qty_update', response_class=JSONResponse)
def qty_update(request: Request, product_id: str = Query(...), flag: bool = Query(...)):
    user = get_current_user(request)
    user_data = get_user_mail(user)
    if user_data == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    ack = update_cart_product(user_data['id'],product_id,flag)
    if ack:
        return JSONResponse(status_code=200, content={"success": True, "message": "Quantity updated successfully"})
    else:
        return JSONResponse(status_code=400, content={"success": False, "message": "Not Enough Stock Available"})

@router.get('/order_confirmed', response_class=HTMLResponse)
def order_confirmed(request: Request):
    user = get_current_user(request)
    categories = get_all_category()
    user_data = get_user_mail(user)
    if user_data == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    res = checkout_cart(user_data['id'])
    if res['message'] == 'False':
        return RedirectResponse(url='/404')
    elif res['message'] == 'Error':
        message = res['response']
        product_id = res.get('product_id',None)
        return templates.TemplateResponse("out_of_stock.html",{"request":request,"user":user,"categories":categories,"message":message,"product_id":product_id})
    
    else:
        order_data = get_order(res['order_id'])
        if order_data == None:
            return RedirectResponse(url='/404')
        temp = {}
        temp['order_id'] = order_data['id']
        temp['order_date'] = order_data['order_date']
        temp['grand_total'] = order_data['total_price']
        temp['product_data'] = []
        for prod_id, qty in order_data['product_data'].items():
            product_data = {}
            product = get_product(prod_id)
            product_data['name'] = product['name']
            product_data['price'] = product['price']
            product_data['stock'] = qty
            product_data['total_price'] = str(int(product['price']) * qty)
            temp['product_data'].append(product_data)
        order_data = temp
        return templates.TemplateResponse("order-confirmed.html",{"request":request,"user":user,"categories":categories,'order_data':order_data})

    
@router.get('/stock_check', response_class=JSONResponse)
def stock_check(request: Request, product_id: str = Query(...), quantity: int = Query(...)):
    product = get_product(product_id)
    if quantity > product['stock']:
        return JSONResponse(status_code=400, content={"success": False, "message": "Not enough stock available"})
    return JSONResponse(status_code=200, content={"success": True, "message": "Stock available"})


@router.get('/sort_category/{cat_id}/{sort}')
def cat_sort_page(request: Request, cat_id: str, sort: str):
    user = get_current_user(request)
    categories = get_all_category()
    category = get_category(cat_id)
    if category == None:
        return RedirectResponse(url="/404")
    elif sort not in ['1','-1']:
        return RedirectResponse(url="/404")
    products = get_product_by_cat_id_sort(cat_id,int(sort))
    return templates.TemplateResponse("users_category.html",{'request':request,"user":user,"category":category,"categories":categories,"products":products})

@router.get('/500')
def server_error(request: Request):
    return templates.TemplateResponse("500.html",{"request":request},status_code=500)

@router.get('/user_profile', response_class=HTMLResponse)
def user_profile(request: Request, response: Response):
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url="/user_login")
    user_data = get_user_mail(user)
    if user_data == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    categories = get_all_category()
    orders = get_order_user(user_data['id'])
    order_list = []
    for i in orders:
        temp = {}
        temp['order_id'] = i['id']
        temp['order_date'] = i['order_date']
        temp['grand_total'] = i['total_price']
        temp['product_data'] = []
        for prod_id, qty in i['product_data'].items():
            product_data = {}
            product = get_product(prod_id)
            product_data['name'] = product['name']
            product_data['base_feature'] = product['base_feature']
            product_data['images'] = product['images']
            product_data['price'] = product['price']
            product_data['stock'] = qty
            product_data['total_price'] = str(int(product['price']) * qty)
            temp['product_data'].append(product_data)
        order_list.append(temp)
    response.headers["Cache-Control"] = "no-cache, no-store"
    success = request.session.get('success',None)
    return templates.TemplateResponse("user_profile.html",{"request":request,"user":user,"user_data":user_data,"categories":categories,"orders":order_list,"success":success})

@router.get('/user_edit_profile', response_class=HTMLResponse)
def user_edit_profile(request: Request):
    user = get_current_user(request)
    user_data = get_user_mail(user)
    if user_data == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    categories = get_all_category()
    return templates.TemplateResponse("edit_user.html",{"request":request,"user":user,"user_data":user_data,"categories":categories})

@router.post('/user_profile_update', response_class=RedirectResponse)
def user_edit_profile(request: Request,response: Response, name:str = Form(...), address: str=Form(...)):
    user = get_current_user(request)
    user_data = get_user_mail(user)
    if user_data == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    categories = get_all_category()
    user = User(name=name,email=user_data['email'],address=address,password=user_data['password'],id=user_data['id'])
    ack = update_user(user,user_data['id'])
    if ack == False:
        return templates.TemplateResponse("edit_user.html",{"request":request,"error":"Something went wrong","user":user,"categories":categories,"user_data":user_data})
    elif ack == True:
        request.session['success'] = "Profile updated successfully"
        return RedirectResponse(url="/user_profile",status_code=303)
    else:
        return templates.TemplateResponse("500.html",{"request":request})
    
    
@router.get('/user_forgot_password', response_class=HTMLResponse)
def forgot_password(request: Request):
    return templates.TemplateResponse("forgot_pass_main.html",{"request":request,'role':'user'})

@router.get('/verify_email', response_class=HTMLResponse)
def verify_email(request: Request, email: str):
    user = get_user_mail(email)
    login_user(request,str(email),'temp')
    if user == None:
        return templates.TemplateResponse("forgot_pass_main.html",{"request":request,"error":"User not found"})
    return templates.TemplateResponse("forgot_pass_sec.html",{"request":request,"user":user})

@router.post('/user_reset_pass')
def reset_password(request: Request, email: str= Form(...), password: str = Form(...)):
    temp_user = get_temp_user(request)
    user = get_user_mail(temp_user)
    if user == None:
        logout_user(request)
        return RedirectResponse(url="/404")
    logout_user(request)
    if temp_user != email:
        return templates.TemplateResponse("forgot_pass_main.html",{"request":request,"error":"Invalid email","user":user})
    if user == None:
        return templates.TemplateResponse("forgot_pass_main.html",{"request":request,"error":"User not found"})
    password = hash_password(password)
    ack = update_user(User(name=user['name'],email=user['email'],password=password,address=user['address'],id=user['id']),user['id'])
    if ack:
        return templates.TemplateResponse("forgot_pass_main.html",{"request":request,"success":"Password updated successfully"})
    else:
        return templates.TemplateResponse("500.html",{"request":request})
    
@router.get('/auth_pass_res', response_class=HTMLResponse)
def auth_pass_res(request: Request):
    user = get_current_user(request)
    if user == None:
        return RedirectResponse(url="/404")
    user = get_user_mail(user)
    return templates.TemplateResponse("forgot_pass_auth.html",{"request":request,"user":user})

@router.post('/auth_pass_res', response_class=RedirectResponse)
def auth_pass_update(request: Request, current_password: str = Form(...), password: str = Form(...)):
    user = get_current_user(request)
    user_data = get_user_mail(user)
    password = hash_password(password)
    if verify_password(user_data['password'],current_password) == False:
        return templates.TemplateResponse("forgot_pass_auth.html",{"request":request,"message":"Invalid password","user":user_data})
    ack = update_user(User(name=user_data['name'],email=user_data['email'],password=password,address=user_data['address'],id=user_data['id']),user_data['id'])
    logout_user(request)
    if ack:
        return templates.TemplateResponse("user_login.html",{"request":request,"message":"Password updated successfully"})
    else:
        return templates.TemplateResponse("500.html",{"request":request})
    
@router.get('/user_search_order', response_class=HTMLResponse)
def user_search_order(request: Request, response: Response, query: str = Query(...)):
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url="/user_login")
    user_data = get_user_mail(user)
    categories = get_all_category()
    orders = get_order_user(user_data['id'])
    order_list = []
    for i in orders:
        temp = {}
        temp['order_id'] = i['id']
        temp['order_date'] = i['order_date']
        temp['grand_total'] = i['total_price']
        temp['product_data'] = []
        for prod_id, qty in i['product_data'].items():
            product_data = {}
            product = get_product(prod_id)
            product_data['name'] = product['name']
            product_data['base_feature'] = product['base_feature']
            product_data['images'] = product['images']
            product_data['price'] = product['price']
            product_data['stock'] = qty
            product_data['total_price'] = str(int(product['price']) * qty)
            temp['product_data'].append(product_data)
        product_name = [i['name'] for i in temp['product_data']]
        if re.search(query, ' '.join(product_name), re.IGNORECASE):
            order_list.append(temp)
        
    response.headers["Cache-Control"] = "no-cache, no-store"
    return templates.TemplateResponse("user_profile.html",{"request":request,"user":user,"user_data":user_data,"categories":categories,"orders":order_list})