# Changelog

## [1.6.0](https://github.com/tuxpeople/python-ipam/compare/v1.5.0...v1.6.0) (2026-09-25)


### Features

* **api:** add upsert endpoint for DHCP ranges ([0584d99](https://github.com/tuxpeople/python-ipam/commit/0584d99166c91f4663aa3e11e641cff8ade94630))


### Bug Fixes

* apply network/hostname normalization and CIDR-lock everywhere ([f4caf74](https://github.com/tuxpeople/python-ipam/commit/f4caf74ed035b4cc47c83bb58c322bfeae519869))

## [1.5.0](https://github.com/tuxpeople/python-ipam/compare/v1.4.0...v1.5.0) (2026-09-25)


### Features

* **api:** add upsert endpoints for networks and hosts ([38bef44](https://github.com/tuxpeople/python-ipam/commit/38bef44071abd6ebf61111f903ceb6d4699b3f55))

## [1.4.0](https://github.com/tuxpeople/python-ipam/compare/v1.3.0...v1.4.0) (2026-09-25)


### Features

* **import:** strip matching network domains from hostnames ([b044264](https://github.com/tuxpeople/python-ipam/commit/b0442649dcc2070badb2cd90f37342c985670d02))

## [1.3.0](https://github.com/tuxpeople/python-ipam/compare/v1.2.0...v1.3.0) (2026-09-25)


### Features

* **hosts:** display last seen timestamps in the host table ([3d945f7](https://github.com/tuxpeople/python-ipam/commit/3d945f7b06f9aea384bf4474d6d48ad0c02a2750))
* **import:** support updates to existing hosts by IP address ([9286c26](https://github.com/tuxpeople/python-ipam/commit/9286c2614fe1827776a24d44d7decc40299bf94e))

## [1.2.0](https://github.com/tuxpeople/python-ipam/compare/v1.1.6...v1.2.0) (2026-09-25)


### Features

* **import:** support optional network metadata and updates ([c7ad8d6](https://github.com/tuxpeople/python-ipam/commit/c7ad8d606afae971c2a2d21c3c0d7a8a63dd5d4e))


### Bug Fixes

* **import:** normalize network addresses before matching and saving ([650e6c5](https://github.com/tuxpeople/python-ipam/commit/650e6c5b83fe302f136a4ed604c04c730019c2c9))
* **ui:** mark JSON import as available ([e812adf](https://github.com/tuxpeople/python-ipam/commit/e812adf30b5375618821aab5d27cea7bbf7dfcd8))

## [1.1.6](https://github.com/tuxpeople/python-ipam/compare/v1.1.5...v1.1.6) (2026-09-09)


### Bug Fixes

* **run_tests:** point coverage at the ipam package ([2cf414b](https://github.com/tuxpeople/python-ipam/commit/2cf414b561970b1c493d7ffe7fdc728ab93c93d8))


### Container

* bump pip to &gt;=26.2 to clear wheel-install CVEs ([#66](https://github.com/tuxpeople/python-ipam/issues/66)) ([e373920](https://github.com/tuxpeople/python-ipam/commit/e37392057b0c547af5f29bf3b4c8a3a13113bffb))
* drop pip/setuptools/wheel from the runtime venv ([#67](https://github.com/tuxpeople/python-ipam/issues/67)) ([a02cb90](https://github.com/tuxpeople/python-ipam/commit/a02cb90119bda16c4f5625e0d562d04fabf78876))


### Documentation

* add MCP server section and pre-commit checklist ([c431382](https://github.com/tuxpeople/python-ipam/commit/c4313821cce34e2cf53689cf615f55143b37e732))
* **features:** drop stale sprint section and template superseded by GH issue form ([e17a355](https://github.com/tuxpeople/python-ipam/commit/e17a355207894e79aad672091e250d5f78b81996))
* **issue-template:** add out-of-scope field to feature request ([9d97428](https://github.com/tuxpeople/python-ipam/commit/9d97428fadc4716bb9c045d5d273832d1f748dc2))
