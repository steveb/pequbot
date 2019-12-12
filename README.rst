=======
pequbot
=======

pequbot is an IRC bot which will make periodic queries to REST APIs and
message channels with the results. It supports querying the following
services:

- https://launchpad.net
- https://storyboard.openstack.org
- https://bugzilla.redhat.com
- https://review.opendev.org

Other services can be added through a simple YAML configuration,
as long as the query is an unauthenticated GET request which returns JSON
as the response.

To install::

    $ sudo python setup.py install

Developers
==========

Report bugs:

 * https://github.com/steveb/pequbot/issues

Browse code:

 * https://github.com/steveb/pequbot

Clone:

 * https://github.com/steveb/pequbot.git

License
=======

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
