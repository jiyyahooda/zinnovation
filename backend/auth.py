import hashlib, secrets, time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from backend import config
from backend.db.connection import connection

router=APIRouter(prefix='/api/auth',tags=['authentication'])
class Login(BaseModel):
    username:str
    password:str

def admin(request:Request):
    # JSON mutations plus SameSite=Strict cookies prevent cross-site form requests.
    origin=request.headers.get('origin')
    if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
        raise HTTPException(403,'Cross-origin admin request denied')
    token=request.cookies.get('civicflux_session','')
    with connection() as db:
        row=db.execute('SELECT actor FROM sessions WHERE token_hash=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
    if not row: raise HTTPException(401,'Admin login required')
    return row['actor']

@router.post('/login')
def login(body:Login,response:Response):
    valid=secrets.compare_digest(hashlib.sha256(body.username.encode()).digest(), hashlib.sha256(config.ADMIN_ID.encode()).digest())
    valid=secrets.compare_digest(hashlib.sha256(body.password.encode()).digest(), hashlib.sha256(config.ADMIN_PASSWORD.encode()).digest()) and valid
    if not valid: raise HTTPException(401,'Invalid credentials')
    token=secrets.token_urlsafe(32)
    with connection() as db:
        db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
        db.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),config.ADMIN_ID,time.time()+28800))
    response.set_cookie('civicflux_session',token,httponly=True,samesite='strict',max_age=28800)
    return {'role':'admin','actor':config.ADMIN_ID}

@router.get('/me')
def me(actor:str=Depends(admin)): return {'role':'admin','actor':actor}

@router.post('/logout')
def logout(request:Request,response:Response):
    with connection() as db: db.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(request.cookies.get('civicflux_session','').encode()).hexdigest(),))
    response.delete_cookie('civicflux_session');return {'ok':True}
