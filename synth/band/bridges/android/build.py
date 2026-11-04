"""Build the dependency-free native Android app with official SDK command tools.
Usage: python build.py --jdk D:/CUBEMX/jre --sdk ROOT/tmp/android-sdk
"""
import argparse,hashlib,json,os,subprocess,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--jdk',required=True);p.add_argument('--sdk',required=True);a=p.parse_args()
base=Path(__file__).resolve().parent;sdk=Path(a.sdk).resolve();jdk=Path(a.jdk).resolve()
tools=next(sdk.rglob('aapt2.exe')).parent;android=next(sdk.rglob('android.jar'))
build=base/'build';build.mkdir(exist_ok=True);classes=build/'classes';classes.mkdir(exist_ok=True);dex=build/'dex';dex.mkdir(exist_ok=True)
env=dict(os.environ,JAVA_HOME=str(jdk));env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','')
def run(*args):subprocess.run([str(x) for x in args],cwd=base,env=env,check=True)
run(tools/'aapt2.exe','compile','--dir',base/'res','-o',build/'resources.zip')
run(tools/'aapt2.exe','link','-o',build/'unsigned.apk','--manifest',base/'AndroidManifest.xml','-I',android,build/'resources.zip')
run(jdk/'bin/javac.exe','-encoding','UTF-8','-source','8','-target','8','-classpath',android,'-d',classes,*sorted((base/'src').rglob('*.java')))
run(jdk/'bin/jar.exe','cf',build/'classes.jar','-C',classes,'.')
run(jdk/'bin/java.exe','-cp',tools/'lib/d8.jar','com.android.tools.r8.D8','--min-api','26','--lib',android,'--output',dex,build/'classes.jar')
with zipfile.ZipFile(build/'unsigned.apk','a',zipfile.ZIP_DEFLATED) as z:
 for f in dex.glob('*.dex'):z.write(f,f.name)
run(tools/'zipalign.exe','-f','-p','4',build/'unsigned.apk',build/'aligned.apk')
key=build/'development.keystore'
if not key.exists():run(jdk/'bin/keytool.exe','-genkeypair','-keystore',key,'-storepass','android','-keypass','android','-alias','starcluster-dev','-keyalg','RSA','-keysize','2048','-validity','3650','-dname','CN=Starcluster Development')
apk=build/'Starcluster-0.4.0.apk'
run(jdk/'bin/java.exe','-jar',tools/'lib/apksigner.jar','sign','--ks',key,'--ks-key-alias','starcluster-dev','--ks-pass','pass:android','--key-pass','pass:android','--out',apk,build/'aligned.apk')
run(jdk/'bin/java.exe','-jar',tools/'lib/apksigner.jar','verify','--verbose',apk)
run(tools/'aapt2.exe','dump','badging',apk)
manifest={'apk':apk.name,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'signing':'development only','package':'cn.starcluster.controller','version':'0.4.0','min_sdk':26,'target_sdk':35}
(build/'result.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
