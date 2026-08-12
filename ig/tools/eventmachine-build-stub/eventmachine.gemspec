Gem::Specification.new do |spec|
  spec.name = "eventmachine"
  spec.version = "1.2.7"
  spec.summary = "Build-only EventMachine compatibility stub"
  spec.description = "Satisfies Jekyll's optional server dependency for static IG builds; it does not implement the EventMachine server API."
  spec.authors = ["QBC IG build tooling"]
  spec.license = "MIT"
  spec.files = ["lib/eventmachine.rb"]
  spec.require_paths = ["lib"]
end

