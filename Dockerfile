FROM mcr.microsoft.com/dotnet/sdk:6.0

# install ilspycmd
RUN dotnet tool install ilspycmd -g
ENV PATH "$PATH:/root/.dotnet/tools"

# install python
RUN apt-get update -y && apt-get install python3-pip -y

# prepare python project
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .

CMD ["python3", "/app/app.py"]
