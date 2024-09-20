module.exports = {
  apps: [{
    name: "pingpong-feeder",
    script: "npm",
    args: "run start",
    cwd: "/path/to/your/project",
    env: {
      NODE_ENV: "production",
    },
  }]
}