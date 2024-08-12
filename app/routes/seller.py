from fastapi import APIRouter,Request,Form, File, UploadFile, Query
from fastapi.responses import HTMLResponse,RedirectResponse
from app.model.models import Seller, Product
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from app.crud.seller import get_seller_mail, add_seller, get_seller, update_seller 
from app.config.session import login_seller, get_current_seller,logout_seller,get_temp_seller
from app.crud.product import get_product_sell, add_new_product, get_product, del_product, update_product,search_product_by_name_seller_id, get_product_name
from app.crud.category import get_all_category, get_category_name
from typing import List
import base64
from datetime import datetime
from app.config.cypher import verify_password,hash_password

router = APIRouter()
templates =  Jinja2Templates(directory='app/templates')

@router.get('/seller_login',response_class= HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("seller_login.html",{'request':request})

@router.post('/seller_login',response_class=HTMLResponse)
def login(request: Request, email:str = Form(...), password:str = Form(...)):
    seller = get_seller_mail(email)
    if seller != None and verify_password(seller['password'],password):
        login_seller(request,str(seller['email']),'auth')
        return RedirectResponse(url='/seller_dashboard',status_code=302)
    return templates.TemplateResponse('seller_login.html',{'request':request,"error":"invalid email or password"})

@router.get('/seller_logout',response_class=RedirectResponse)
def user_logout(request: Request):
    logout_seller(request)
    return RedirectResponse(url='/seller_login')


@router.get('/seller_dashboard', response_class=HTMLResponse)
def landing_page(request: Request):
    try:
        seller = get_current_seller(request)
        seller_info = get_seller_mail(seller)
        if seller_info == None:
            logout_seller(request)
            return RedirectResponse(url='/seller_login')
        products = get_product_sell(seller_info['id'])
        return templates.TemplateResponse("seller_landing.html",{"request":request,"seller":seller,"seller_info":seller_info,"products":products})
    except:
        return RedirectResponse(url='/seller_login')
    
@router.get('/seller_add_product', response_class=HTMLResponse)
def addproductinfo(request: Request):
    try:
        seller = get_current_seller(request)
        categories = get_all_category()
        return templates.TemplateResponse("seller_product.html",{'request':request,"seller":seller,"categories":categories})
    except:
        return RedirectResponse(url='/seller_login')

@router.post('/seller_add_product', response_class=HTMLResponse)
async def addproductinfpr(
    request: Request,
    name: str = Form(...),
    price: str = Form(...),
    base_feature: str = Form(...),
    stock: int = Form(...),
    description: str = Form(...),
    cat_id: str = Form(...),
    images: List[UploadFile] = File(...),
):
    encoded_images = []
    seller = get_current_seller(request)
    if len(images) > 4:
        return templates.TemplateResponse("seller_product.html",{'request':request,"seller":seller,"categories":get_all_category(),'message':'max'})
    for image in images:
        contents = await image.read()
        encoded = base64.b64encode(contents).decode('utf-8')
        encoded_images.append(encoded)
    seller = get_current_seller(request)
    seller_info = get_seller_mail(seller)
    if seller_info == None:
        logout_seller(request)
        return RedirectResponse(url='/seller_login')
    existing_products = get_product_name(name)
    if existing_products != None and existing_products['seller_id'] == seller_info['id']:
        return templates.TemplateResponse("seller_product.html",{'request':request,"seller":seller,"categories":get_all_category(),'message':'exist'})
    product = Product(
        name=name,
        images=encoded_images[::-1],
        price=price,
        base_feature=base_feature,
        stock=stock,
        description=description,
        cat_id=cat_id,
        seller_id=seller_info['id'],
        last_change=str(datetime.now())
    )
    
    ack = add_new_product(product)
    if ack:
        return templates.TemplateResponse("seller_product.html",{'request':request,"seller":seller,"categories":get_all_category(),'message':'success'})
    else:
        return templates.TemplateResponse("seller_product.html",{'request':request,"seller":seller,"categories":get_all_category(),'message':'error'})

@router.get('/seller_product/{product_id}', response_class=HTMLResponse)
def product_info(request: Request, product_id:str):
        seller = get_current_seller(request)
        seller_info = get_seller_mail(seller)
        if seller_info == None:
            logout_seller(request)
            return RedirectResponse(url='/seller_login')
        product = get_product(product_id)
        if product == None:
            return RedirectResponse(url='/404')
        category = get_all_category()
        return templates.TemplateResponse("seller_product_info.html",{'request':request,"seller":seller,"product":product,"categories":category})
    
@router.post('/seller_product_update/{product_id}', response_class=RedirectResponse)
async def update_product_info(request: Request,product_id: str, name:str = Form(...), price:str = Form(...), base_feature:str = Form(...), stock:int = Form(...), description:str = Form(...), cat_id:str = Form(...), images: List[UploadFile] = File(...),existing_images: List[str] = Form(...)):
    seller = get_current_seller(request)
    seller_info = get_seller_mail(seller)
    product = get_product(product_id)
    exist_product = get_product_name(name)
    if exist_product != None and exist_product['seller_id'] == seller_info['id'] and exist_product['id'] != product_id:
        return templates.TemplateResponse("seller_product_info.html",{'request':request,"seller":seller,"product":product,"categories":get_all_category(),'message':'exist'})
    if product['seller_id'] == seller_info['id']:
        product['name'] = name
        product['price'] = price
        product['base_feature'] = base_feature
        product['stock'] = stock
        product['description'] = description
        product['cat_id'] = cat_id
        product['last_change'] = str(datetime.now())
        if images[0].filename != '':
            encoded_images = []
            for image in images:
                contents = await image.read()
                encoded = base64.b64encode(contents).decode('utf-8')
                encoded_images.append(encoded)
            product['images'] = encoded_images[::-1]
        else:
            existing_images = existing_images[0].split(',')
            product['images'] = existing_images
        ack = update_product(product,product_id)
        if ack:
            return templates.TemplateResponse("seller_landing.html",{'request':request,"seller":seller,"seller_info":seller_info,"products":get_product_sell(seller_info['id']),'message':'success'})
        else:
            return templates.TemplateResponse("seller_product_info.html",{'request':request,"seller":seller,"product":product,"categories":get_all_category(),'message':'error'})


@router.get('/seller_product_del/{product_id}', response_class=HTMLResponse)
def delete_product(request: Request, product_id:str):
    seller = get_current_seller(request)
    seller_info = get_seller_mail(seller)
    product = get_product(product_id)
    if product['seller_id'] == seller_info['id']:
        del_product(product_id)
        return RedirectResponse(url='/seller_dashboard')
    
@router.get('/seller_edit_info/', response_class=HTMLResponse)
def seller_update(request: Request):
    seller = get_current_seller(request)
    seller_info = get_seller_mail(seller)
    return templates.TemplateResponse("edit_seller_info.html",{'request':request,"seller":seller,"seller_info":seller_info,})

@router.post('/seller_edit/', response_class=HTMLResponse)
def seller_update(request: Request, name:str = Form(...), phone: str=Form(...)):
    seller=get_current_seller(request)
    seller_data=get_seller_mail(seller)
    if phone.isdigit() != True or len(phone) != 10:
        return templates.TemplateResponse("edit_seller_info.html",{"request":request,"error":"Invalid phone number","seller":seller,"seller_info":seller_data})
    seller=Seller(name=name,email=seller_data['email'],password=seller_data['password'], phone=phone)
    ack=update_seller(seller, seller_data['id'])
    if ack == False:
        return templates.TemplateResponse("edit_seller_info.html",{"request":request,"error":"Email already exist","seller":seller,"seller_info":seller_data})
    elif ack == True:
        seller = get_current_seller(request)
        seller_info = get_seller_mail(seller)
        if seller_info == None:
            logout_seller(request)
            return RedirectResponse(url='/seller_login')
        products = get_product_sell(seller_info['id'])
        return templates.TemplateResponse("seller_landing.html",{"request":request,"seller":seller,"seller_info":seller_info,"products":products,"success":"profile updated successfully"})   
    else:
        return templates.TemplateResponse("500.html",{"request":request})
    
@router.get('/search_product_seller', response_class=HTMLResponse)
def search_product(request: Request, search:str = Query(...)):
    seller = get_current_seller(request)
    seller_info = get_seller_mail(seller)
    if seller_info == None:
        logout_seller(request)
        return RedirectResponse(url='/seller_login')
    products = search_product_by_name_seller_id(seller_info['id'],search)
    return templates.TemplateResponse("seller_landing.html",{"request":request,"seller":seller,"seller_info":seller_info,"products":products})

@router.get('/seller_fogot_password', response_class=HTMLResponse)
def fogot_password(request: Request):
    return templates.TemplateResponse("forgot_pass_main_seller.html",{'request':request,'role':'seller'})

@router.get('/verfiy_seller_email', response_class=HTMLResponse)
def verify_email(request: Request, email: str):
    seller = get_seller_mail(email)
    login_seller(request,str(email),'temp')
    if seller == None:
        return templates.TemplateResponse("forgot_pass_main_seller.html",{"request":request,"error":"Seller not found","role":"seller"})
    return templates.TemplateResponse("forgot_pass_sec_seller.html",{"request":request,"seller":seller})

@router.post('/seller_reset_pass')
def reset_password(request: Request, email: str= Form(...), password: str = Form(...)):
    temp_seller = get_temp_seller(request)
    seller = get_seller_mail(temp_seller)
    logout_seller(request)
    if temp_seller != email:
        return templates.TemplateResponse("forgot_pass_main_seller.html",{"request":request,"error":"Invalid email","seller":seller,"role":"seller"})
    if seller == None:
        return templates.TemplateResponse("forgot_pass_main_seller.html",{"request":request,"error":"User not found","seller":seller,"role":"seller"})
    password = hash_password(password)
    ack = update_seller(Seller(name=seller['name'],email=seller['email'],password=password,phone=seller['phone'],id=seller['id']),seller['id'])
    if ack:
        return templates.TemplateResponse("forgot_pass_main_seller.html",{"request":request,"success":"Password updated successfully","role":"seller","seller":seller})
    else:
        return templates.TemplateResponse("500.html",{"request":request})
    
@router.get('/auth_pass_res_seller', response_class=HTMLResponse)
def auth_pass_res(request: Request):
    seller = get_current_seller(request)
    if seller == None:
        return RedirectResponse(url="/404")
    seller = get_seller_mail(seller)
    return templates.TemplateResponse("forgot_pass_auth_seller.html",{"request":request,"seller":seller})

@router.post('/auth_pass_res_seller', response_class=RedirectResponse)
def auth_pass_update(request: Request, current_password: str = Form(...), password: str = Form(...)):
    seller = get_current_seller(request)
    seller_data = get_seller_mail(seller)
    password = hash_password(password)
    if verify_password(seller_data['password'],current_password) == False:
        return templates.TemplateResponse("forgot_pass_auth_seller.html",{"request":request,"message":"Invalid password","seller":seller_data})
    ack=update_seller(Seller(name=seller_data['name'],email=seller_data['email'],password=password,phone=seller_data['phone'],id=seller_data['id']),seller_data['id'])
    logout_seller(request)
    if ack:
        return templates.TemplateResponse("seller_login.html",{"request":request,"success":"Password updated successfully"})
    else:
        return templates.TemplateResponse("500.html",{"request":request})
    