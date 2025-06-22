#!/bin/bash

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Define virtual environment directory
VENV_DIR="venv"

# Check if virtual environment exists, create if not
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    # Make sure python3-venv is installed
    if ! python3 -m venv --help &> /dev/null; then
        echo "The venv module is not available. Installing python3-venv..."
        sudo apt-get update && sudo apt-get install -y python3-venv python3-full
    fi

    # Create virtual environment
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please install python3-venv package."
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing dependencies with trusted hosts..."
pip install --upgrade pip
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo "Installation complete!"
    echo ""
    echo "To run the application, first activate the virtual environment:"
    echo "    source $VENV_DIR/bin/activate"
    echo "Then run the application:"
    echo "    python run.py"
    echo ""
    echo "You can deactivate the virtual environment when done:"
    echo "    deactivate"
else
    echo "Installation failed!"
fi
