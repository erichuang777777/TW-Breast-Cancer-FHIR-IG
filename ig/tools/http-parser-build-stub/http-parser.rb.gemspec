Gem::Specification.new do |spec|
  spec.name = "http_parser.rb"
  spec.version = "0.8.0"
  spec.summary = "Build-only HTTP parser compatibility stub"
  spec.description = "Satisfies Jekyll's optional server dependency for static IG builds; it does not implement an HTTP parser."
  spec.authors = ["QBC IG build tooling"]
  spec.license = "MIT"
  spec.files = ["lib/http_parser.rb"]
  spec.require_paths = ["lib"]
end

