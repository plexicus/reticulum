require 'redis'
require 'json'

class Worker
  def initialize
    @redis = Redis.new(host: 'redis', port: 6379)
  end
  
  def process_job(job_data)
    # CRITICAL VULNERABILITY: Command injection
    command = job_data['command']
    # Directly executing user-controlled input
    result = `#{command}`
    
    puts "Executed: #{command}"
    puts "Result: #{result}"
    result
  end
  
  def run
    loop do
      job = @redis.blpop('jobs', timeout: 5)
      if job
        job_data = JSON.parse(job[1])
        process_job(job_data)
      end
    end
  end
end

worker = Worker.new
worker.run
