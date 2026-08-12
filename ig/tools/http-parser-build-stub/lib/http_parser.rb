# Build-only compatibility stub. Static Jekyll builds do not use this API.
module Http
  class Parser
    def initialize(*)
      raise NotImplementedError, "HTTP parser is unavailable in the build-only Jekyll runtime"
    end
  end
end

