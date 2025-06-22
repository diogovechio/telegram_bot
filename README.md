# Pedro Leblon Bot

## Installation

### Dependencies

This project requires several Python dependencies which are listed in the `requirements.txt` file.

The installation scripts now create a virtual environment to avoid conflicts with system packages and to work with Python's externally managed environment restrictions.

#### Windows Users

Run the `install_dependencies.bat` script:

```
install_dependencies.bat
```

#### Linux/Mac Users

Make the script executable and run it:

```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```

#### Manual Installation with Virtual Environment

If you prefer to install dependencies manually, you can create and use a virtual environment:

```bash
# Create virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate.bat

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

## Configuration

Before running the bot, make sure to configure:

1. `bot_configs.json` - General bot configuration
2. `secrets.json` - API keys and tokens

## Running the Bot

To start the bot, first activate the virtual environment (if not already activated):

```bash
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate.bat
```

Then run the application:

```bash
python run.py
```

When you're done, you can deactivate the virtual environment:

```bash
deactivate
```
