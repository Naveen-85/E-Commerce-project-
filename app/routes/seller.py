from fastapi import APIRouter,Request,Form, File, UploadFile
from fastapi.responses import HTMLResponse,RedirectResponse
from app.model.models import Seller, Product
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from app.crud.seller import get_seller_mail, add_seller, get_seller, update_seller 
from app.config.session import login_seller, get_current_seller,logout_seller
from app.crud.product import get_product_sell, add_new_product, get_product, del_product, update_product
from app.crud.category import get_all_category, get_category_name
from typing import List
import base64
from datetime import datetime
from app.config.cypher import verify_password

router = APIRouter()
templates =  Jinja2Templates(directory='app/templates')

@router.get('/seller_login',response_class= HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("seller_login.html",{'request':request})

@router.post('/seller_login',response_class=HTMLResponse)
def login(request: Request, email:str = Form(...), password:str = Form(...)):
    seller = get_seller_mail(email)
    if seller != None and verify_password(seller['password'],password):
        login_seller(request,str(seller['email']))
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
    for image in images:
        contents = await image.read()
        encoded = base64.b64encode(contents).decode('utf-8')
        encoded_images.append(encoded)
    seller = get_current_seller(request)
    seller_info = get_seller_mail(seller)
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
        product = get_product(product_id)
        category = get_all_category()
        return templates.TemplateResponse("seller_product_info.html",{'request':request,"seller":seller,"product":product,"categories":category})
    
@router.post('/seller_product_update/{product_id}', response_class=RedirectResponse)
async def update_product_info(request: Request,product_id: str, name:str = Form(...), price:str = Form(...), base_feature:str = Form(...), stock:int = Form(...), description:str = Form(...), cat_id:str = Form(...), images: List[UploadFile] = File(...),existing_images: List[str] = Form(...)):
    seller = get_current_seller(request)
    seller_info = get_seller_mail(seller)
    product = get_product(product_id)
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
def seller_update(request: Request, name:str = Form(...), email: str=Form(...), phone: str=Form(...)):
    seller=get_current_seller(request)
    seller_data=get_seller_mail(seller)
    seller=Seller(name=name,email=email,phone=phone)
    ack=update_seller(seller, seller_data['id'])
    if ack == False:
        return templates.TemplateResponse("edit_seller_info.html",{"request":request,"error":"Email already exist","seller":seller})
    elif ack == True:
        return templates.TemplateResponse("edit_seller_info.html",{"request":request,"success":"Profile updated successfully","seller":seller})
    else:
        return templates.TemplateResponse("500.html",{"request":request})
    
    