@echo off
echo Installing dependencies with trusted hosts...
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
echo Installation complete!
pause