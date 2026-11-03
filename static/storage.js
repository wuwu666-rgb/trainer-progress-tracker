let database;
export async function openDB(){
 if(database)return database;
 database=await new Promise((resolve,reject)=>{const r=indexedDB.open('repbook-v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('kv');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
 return database;
}
export async function get(key){const db=await openDB();return new Promise((resolve,reject)=>{const r=db.transaction('kv').objectStore('kv').get(key);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
export async function put(key,value){return change(key,()=>value);}
export async function change(key,update){
 const db=await openDB();
 return new Promise((resolve,reject)=>{const tx=db.transaction('kv','readwrite'),s=tx.objectStore('kv');let value;const r=s.get(key);r.onsuccess=()=>{try{value=update(r.result);if(value===undefined)s.delete(key);else s.put(value,key);}catch(e){tx.abort();reject(e);}};tx.oncomplete=()=>resolve(value);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('Could not save on this device.'));});
}
export async function list(prefix){const db=await openDB();return new Promise((resolve,reject)=>{const out=[],r=db.transaction('kv').objectStore('kv').openCursor();r.onsuccess=()=>{const c=r.result;if(c){if(String(c.key).startsWith(prefix))out.push(c.value);c.continue();}else resolve(out);};r.onerror=()=>reject(r.error);});}
export async function clearPrivate(){const db=await openDB();return new Promise((resolve,reject)=>{const tx=db.transaction('kv','readwrite');tx.objectStore('kv').clear();tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);});}
export const newId=()=>crypto.randomUUID();
