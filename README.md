# Wingo AI Predictor

A Docker-based AI prediction system for analyzing Wingo game patterns.

## Architecture

Scraper → MongoDB → Trainer → API → Dashboard

## Services

### Scraper
Collects game results and stores them in MongoDB.

### Trainer
Trains a machine learning model using historical results.

### API
Serves predictions via a REST endpoint.

### Dashboard
Streamlit interface to visualize predictions.

## Run the System

Clone the repository:

```bash
git clone https://github.com/yourname/wingo-ai-system.git
cd wingo-ai-system