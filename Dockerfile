FROM minizinc/minizinc:latest AS minizinc
FROM gurobi/python:latest

WORKDIR /app

RUN apt-get update && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pulp==3.2.2 \
    minizinc \
    z3-solver==4.15.3.0 \
    highspy==1.11.0 

COPY --from=minizinc /usr/local/bin/ /usr/local/bin/
COPY --from=minizinc /usr/local/share/minizinc /usr/local/share/minizinc
COPY --from=minizinc /usr/local/lib/ /usr/local/lib/

ENV PATH="/usr/local/bin:${PATH}"
COPY source/ /app/source/
COPY run.sh /app/
RUN chmod +x /app/run.sh
ENV PYTHONPATH="/app"

RUN mkdir -p /app/res/MIP /app/res/CP /app/res/SAT

# Verify Gecode is available
RUN minizinc --solvers-json | grep -i gecode || echo "Gecode not found"

RUN python --version && \
    minizinc --version && \
    python -c "import gurobipy; print('Gurobi OK')" && \
    python -c "import minizinc; print('MiniZinc Python OK')"
CMD ["./run.sh", "all"]
