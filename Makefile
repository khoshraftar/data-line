# Simple Makefile for Data Line Django Project

.PHONY: help install runserver

# Default target
help:
	@echo "Available commands:"
	@echo "  make install   - Install requirements"
	@echo "  make runserver - Run Django development server"

# Install requirements
install:
	@echo "Installing requirements..."
	pip install -r requirements.txt
	@echo "Requirements installed successfully!"

# Run Django development server
runserver:
	@echo "Starting Django development server..."
	python manage.py runserver 127.0.0.1:8001 