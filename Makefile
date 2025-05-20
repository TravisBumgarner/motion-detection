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
	@git pull
	@git push