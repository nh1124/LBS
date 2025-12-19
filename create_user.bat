@echo off
set /p EMAIL="Enter user email: "
set /p NAME="Enter user name: "

echo Creating user...
curl -X POST http://localhost:8300/api/lbs/users/ ^
     -H "Content-Type: application/json" ^
     -d "{\"email\": \"%EMAIL%\", \"name\": \"%NAME%\"}"

echo.
echo Please copy the api_key from the response above and paste it into the LBS UI Authentication modal.
pause
