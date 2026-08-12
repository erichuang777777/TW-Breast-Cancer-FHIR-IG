# Build-only compatibility stub. The QBC IG invokes `jekyll build`, never `jekyll serve`.
module EventMachine
  def self.run(*)
    raise NotImplementedError, "EventMachine is unavailable in the build-only Jekyll runtime"
  end
end

