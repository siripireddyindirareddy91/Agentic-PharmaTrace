import {NextRequest,NextResponse} from 'next/server';
import {cookies} from 'next/headers';
export const dynamic='force-dynamic';
async function proxy(req:NextRequest,{params}:{params:Promise<{path:string[]}>}){
  const {path}=await params;const route=path.join('/');const jar=await cookies();
  if(route==='auth/logout'){jar.delete('pt_session');return NextResponse.json({ok:true})}
  if(!route.startsWith('auth/')&&!jar.get('pt_session')) return NextResponse.json({detail:'Sign in required'},{status:401});
  const base=process.env.BACKEND_INTERNAL_URL||process.env.API_URL||'http://127.0.0.1:8000';
  try{
    const headers=new Headers();if(req.headers.get('content-type'))headers.set('content-type',req.headers.get('content-type')!);
    const session=jar.get('pt_session')?.value;if(session)headers.set('Authorization','Bearer '+session);
    const res=await fetch(base+'/api/'+route+req.nextUrl.search,{method:req.method,headers,body:['GET','HEAD'].includes(req.method)?undefined:await req.arrayBuffer(),cache:'no-store',signal:AbortSignal.timeout(55000)});
    if(route.startsWith('auth/')&&res.ok&&req.method==='POST'){
      const data=await res.json();if(data.token){jar.set('pt_session',data.token,{httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'lax',maxAge:28800,path:'/'});delete data.token}return NextResponse.json(data);
    }
    return new NextResponse(await res.arrayBuffer(),{status:res.status,headers:{'content-type':res.headers.get('content-type')||'application/json',...(res.headers.get('content-disposition')?{'content-disposition':res.headers.get('content-disposition')!}:{}),'Cache-Control':'no-store'}});
  }catch(error){console.error('Backend request failed',error instanceof Error?error.message:'unknown');return NextResponse.json({detail:'The API is temporarily unavailable. Please retry.'},{status:503})}
}
export {proxy as GET,proxy as POST,proxy as PUT,proxy as PATCH};
