@echo off

copy D:\vue3\chumpower\*.config.js C:\chumpower-backup\front\
copy D:\vue3\chumpower\*.json C:\chumpower-backup\front\
copy D:\vue3\chumpower\*.bat C:\chumpower-backup\front\
copy D:\vue3\chumpower\.eslintrc.js C:\chumpower-backup\front\
copy D:\vue3\chumpower\.gitignore C:\chumpower-backup\front\

copy D:\vue3\chumpower\public\*.* C:\chumpower-backup\front\public

c:\windows\system32\xcopy D:\vue3\chumpower\src\*.js C:\chumpower-backup\front\src\ /E
c:\windows\system32\xcopy D:\vue3\chumpower\src\*.vue C:\chumpower-backup\front\src\ /E

c:\windows\system32\xcopy D:\vue3\chumpower\src\views\*.vue C:\chumpower-backup\front\src\views\ /E
c:\windows\system32\xcopy D:\vue3\chumpower\src\assets\*.* C:\chumpower-backup\front\src\assets\ /E
copy D:\vue3\chumpower\src\components\*.vue C:\chumpower-backup\front\src\components\
copy D:\vue3\chumpower\src\styles\*.scss C:\chumpower-backup\front\src\styles\
copy D:\vue3\chumpower\src\store\index.js C:\chumpower-backup\front\src\store\
copy D:\vue3\chumpower\src\router\index.js C:\chumpower-backup\front\src\router\
copy D:\vue3\chumpower\src\mixins\*.js C:\chumpower-backup\front\src\mixins\

copy C:\vue\chumpower\.env  C:\chumpower-backup\server
c:\windows\system32\xcopy C:\vue\chumpower\server\*.* C:\chumpower-backup\server\ /E
copy C:\vue\chumpower\venv\*.* C:\chumpower-backup\venv

@echo on