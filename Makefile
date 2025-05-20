help:
	@echo "Makefile for managing the project"
	@echo "Usage:"
	@echo "  make bootstrap   - Bootstrap the project"
	@echo "  make sync       - Sync the project with the remote repository"
	@echo "  make help       - Show this help message"

bootstrap: 
	@echo "Bootstraping the project..."
	@chmod +x ./scripts/bootstrap.sh
	@./scripts/bootstrap.sh

sync:
	@git add .
	@git commit -m "Syncing with remote repository"
	@git pull
	@git push

server:
	@echo "Starting the server..."
	@. source ~/Desktop/motion-detection/.venv/bin/activate
	@python3 -m flask run --host=0.0.0.0 --port=5000