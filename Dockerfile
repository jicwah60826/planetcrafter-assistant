FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY PlanetCrafterAssistant.csproj ./
RUN dotnet restore

COPY . .
RUN dotnet publish -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

COPY --from=build /app/publish .

# wwwroot/icons is populated by the Python parser — mount it as a volume
# so icons persist and can be updated without rebuilding the image
VOLUME ["/app/wwwroot/icons"]

# BUILD_ID is injected at build time via: docker build --build-arg BUILD_ID=<value>
ARG BUILD_ID=dev
ENV BUILD_ID=$BUILD_ID

ENV ASPNETCORE_URLS=http://+:8080
ENV ASPNETCORE_ENVIRONMENT=Production

EXPOSE 8080
ENTRYPOINT ["dotnet", "PlanetCrafterAssistant.dll"]