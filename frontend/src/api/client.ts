export async function api<T>(path:string,body?:unknown):Promise<T>{
 const response=await fetch('/api/'+path,{credentials:'same-origin',...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
 if(!response.ok){const error=await response.json().catch(()=>({detail:'Server unavailable'}));throw new Error(typeof error.detail==='string'?error.detail:JSON.stringify(error.detail));}
 return response.json() as Promise<T>;
}
