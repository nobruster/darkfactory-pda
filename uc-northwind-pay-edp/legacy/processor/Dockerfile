FROM maven:3.9.11-eclipse-temurin-21-alpine@sha256:922927df2c662cdd47ddb116443d6bec4696cfae3de1a0ddac8fcc7b87ce61ae AS build

WORKDIR /build
COPY legacy/processor/pom.xml .
RUN mvn --batch-mode dependency:go-offline

COPY legacy/processor/src ./src
COPY contracts/types/01-card-settlement /contracts/types/01-card-settlement
COPY contracts/types/02-instant-payment-events /contracts/types/02-instant-payment-events
COPY contracts/types/03-payment-slip-settlement /contracts/types/03-payment-slip-settlement
COPY contracts/types/04-ted-transfer-settlement /contracts/types/04-ted-transfer-settlement
COPY contracts/types/05-merchant-fee-assessment /contracts/types/05-merchant-fee-assessment
COPY contracts/types/06-merchant-chargeback /contracts/types/06-merchant-chargeback
RUN mvn --batch-mode \
    -Dcontract.fixture.root=/contracts/types/01-card-settlement/main \
    -Dcontract.type02.fixture.root=/contracts/types/02-instant-payment-events/main \
    -Dcontract.type03.fixture.root=/contracts/types/03-payment-slip-settlement/main \
    -Dcontract.type04.fixture.root=/contracts/types/04-ted-transfer-settlement/main \
    -Dcontract.type05.fixture.root=/contracts/types/05-merchant-fee-assessment/main \
    verify

FROM eclipse-temurin:21-jre-alpine@sha256:3f08b13888f595cc49edabea7250ba69499ba25602b267da591720769400e08c

RUN addgroup -S processor && adduser -S -D -H -G processor processor
WORKDIR /app
COPY --from=build /build/target/legacy-processor.jar /app/legacy-processor.jar
USER processor

ENTRYPOINT ["java", "-jar", "/app/legacy-processor.jar"]
