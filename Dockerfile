FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY PlanetCrafterAssistant.csproj ./
RUN dotnet restore

COPY . .
RUN dotnet publish -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

COPY --from=build /app/publish .

ARG BUILD_ID=dev
ENV BUILD_ID=$BUILD_ID

ENV ASPNETCORE_URLS=http://+:8080
ENV ASPNETCORE_ENVIRONMENT=Production

EXPOSE 8080
ENTRYPOINT ["dotnet", "PlanetCrafterAssistant.dll"]