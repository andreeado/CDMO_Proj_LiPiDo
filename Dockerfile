FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    build-essential \
    coinor-cbc \
    && apt-get install -y glpk-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pyomo==6.9.2 \
    ply==3.11 \
    wheel==0.45.1 \
    pulp==2.9.0 \
    minizinc==0.9.0 \
    z3-solver==4.15.3.0 \
    highspy==1.11.0 \
    setuptools==78.1.1

COPY res/ /app/res/
COPY source/ /app/source/
COPY run.sh /app/
RUN chmod +x /app/run.sh
ENV PYTHONPATH="/app"

RUN mkdir -p /app/res/MIP /app/res/CP /app/res/SAT

CMD ["./run.sh", "all"]
