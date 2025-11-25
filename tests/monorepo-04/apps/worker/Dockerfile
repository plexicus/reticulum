FROM ruby:3.0-slim

WORKDIR /app
COPY Gemfile Gemfile.lock ./
RUN bundle install
COPY . .

CMD ["ruby", "worker.rb"]
