.. _news:

Release notes
=============

.. changelog

Unreleased
----------

Added
~~~~~

- Add a :ref:`status.json` webservice, to get the status of a job.
- Respond to HTTP ``OPTIONS`` method requests.
- Add environment variables to override common options. See :doc:`config`.

Documentation
^^^^^^^^^^^^^

- How to add webservices (endpoints). See :ref:`config-services`.
- How to create Docker images. See :ref:`docker`.

Changed
~~~~~~~

- Add a confirmation dialog to the Cancel button.
- Add "Last modified" column to the directory listings of log files and item feeds.
- Drop support for end-of-life Python version 3.7.

API
^^^

- If the ``egg`` parameter to the :ref:`addversion.json` webservice is not a ZIP file, use the error message, "egg is not a ZIP file (if using curl, use egg=@path not egg=path)".
- Clarify some error messages, for example:

  - ``'project' parameter is required`` instead of ``'project'``
  - ``project 'myproject' not found`` instead of ``'myproject'``
  - ``exception class: message`` instead of ``message``
  - ``ValueError: Unknown or corrupt egg`` instead of ``TypeError: 'tuple' object is not an iterator``

CLI
^^^

- Correct the usage message and long description, remove all ``twistd`` subcommands, and remove the ``--nodaemon`` and ``--python=`` options, which it overrides.
- Run the ``scrapyd.__main__`` module instead of the ``scrapyd.scripts.scrapyd_run`` module.

Fixed
~~~~~

- The :ref:`schedule.json` webservice sets the ``node_name`` field in error responses.
- The :ref:`cancel.json` webservice now works on Windows.
- The :ref:`jobs_to_keep` setting no longer causes an error if a file to delete can't be deleted (for example, if the file is open on Windows).
- When managing multiple projects, the next pending job for all but one project was unreported by the :ref:`daemonstatus.json` and :ref:`listjobs.json` webservices, and was not cancellable by the :ref:`cancel.json` webservice.

1.4.3 (2023-09-25)
------------------

Changed
~~~~~~~

- Change project from comma-separated list to bulleted list on landing page. (@bsekiewicz)

Fixed
~~~~~

- Fix "The process cannot access the file because it is being used by another process" on Windows.

1.4.2 (2023-05-01)
------------------

Added
~~~~~

- Add ``spiderqueue`` configuration option for custom spider queue.
- Add support for the X-Forwarded-Prefix HTTP header. Rename this header using the :ref:`prefix_header` configuration option.

Changed
~~~~~~~

- ``scrapyd.spiderqueue.SqliteSpiderQueue`` is initialized with a ``scrapyd.config.Config`` object and a project name, rather than a SQLite connection string (i.e. database file path).
- If ``dbs_dir`` is set to ``:memory:`` or to a URL, it is passed through without modification and without creating a directory to ``scrapyd.jobstorage.SqliteJobStorage`` and ``scrapyd.spiderqueue.SqliteSpiderQueue``.
- ``scrapyd.utils.get_spider_queues`` defers the creation of the ``dbs_dir`` directory to the spider queue implementation.

1.4.1 (2023-02-10)
------------------

Fixed
~~~~~

- Encode the ``FEEDS`` command-line argument as JSON.

1.4.0 (2023-02-07)
------------------

Added
~~~~~

- Add ``items_url`` and ``log_url`` to the response from the :ref:`listjobs.json` webservice. (@mxdev88)
- Scrapy 2.8 support. Scrapyd sets ``LOG_FILE`` and ``FEEDS`` command-line arguments, instead of ``SCRAPY_LOG_FILE`` and ``SCRAPY_FEED_URI`` environment variables.
- Python 3.11 support.
- Python 3.12 support. Use ``packaging.version.Version`` instead of ``distutils.LooseVersion``. (@pawelmhm)

Changed
~~~~~~~

- Rename environment variables to avoid spurious Scrapy deprecation warnings.

  - ``SCRAPY_EGG_VERSION`` to ``SCRAPYD_EGG_VERSION``
  - ``SCRAPY_FEED_URI`` to ``SCRAPYD_FEED_URI``
  - ``SCRAPY_JOB`` to ``SCRAPYD_JOB``
  - ``SCRAPY_LOG_FILE`` to ``SCRAPYD_LOG_FILE``
  - ``SCRAPY_SLOT`` to ``SCRAPYD_SLOT``
  - ``SCRAPY_SPIDER`` to ``SCRAPYD_SPIDER``

  .. attention::

    These are undocumented and unused, and may be removed in future versions. If you use these environment variables, please `report your use in an issue <https://github.com/scrapy/scrapyd/issues>`__.

Removed
~~~~~~~

- Scrapy 1.x support.
- Python 3.6 support.
- Unmaintained files (Debian packaging) and unused code (``scrapyd/script.py``).

Fixed
~~~~~

- Print Scrapyd's version instead of Twisted's version with ``--version`` (``-v``) flag. (@niuguy)
- Override Scrapy's ``LOG_STDOUT`` setting to ``False`` to suppress logging output for :ref:`listspiders.json` webservice. (@Lucioric2000)

1.3.0 (2022-01-12)
------------------

Added
~~~~~

- Add support for HTTP authentication.
- Make optional the ``project`` argument to the :ref:`listjobs.json` webservice, to easily query for all jobs.
- Improve HTTP headers across webservices.
- Add shortcut to jobs page to cancel a job using the :ref:`cancel.json` webservice.
- Add configuration options for job storage class and egg storage class.
- Improve test coverage.
- Python 3.7, 3.8, 3.9, 3.10 support.

Removed
~~~~~~~

- Python 2, 3.3, 3.4, 3.5 support.
- PyPy 2 support.
- Documentation for Ubuntu installs (Zyte no longer maintains the Ubuntu package).

Fixed
~~~~~

- Respect Scrapy's ``TWISTED_REACTOR`` setting.
- Replace deprecated ``SafeConfigParser`` with ``ConfigParser``.

1.2.1 (2019-06-17)
------------------

Fixed
~~~~~

- Fix HTTP header types for newer Twisted versions.
- ``DeferredQueue`` no longer hides a pending job when reaching ``max_proc``.
- The :ref:`addversion.json` webservice now works on Windows.
- test: Update binary eggs to be compatible with Scrapy 1.x.

Removed
~~~~~~~

- Remove deprecated SQLite utilities.

1.2.0 (2017-04-12)
------------------

Added
~~~~~

- Webservice

  - Add the :ref:`daemonstatus.json` webservice.
  - Add a ``_version`` argument to the :ref:`schedule.json` webservice.
  - Add a ``jobid`` argument to the :ref:`schedule.json` webservice.
  - Add the run's PID to the response of the :ref:`listjobs.json` webservice.
  - Include full tracebacks from Scrapy when failing to get spider list.
    This makes debugging deployment problems easier, but webservice output noisier.

- Website

  - Add ``webroot`` configuration option for website root class.
  - Add start and finish times to jobs page.

- Make console script executable.
- Add contributing documentation.
- Twisted 16 support.
- Python 3 support.

Changed
~~~~~~~

- Change ``bind_address`` default to 127.0.0.1, instead of 0.0.0.0, to listen only for connections from localhost.

Removed
~~~~~~~

- Deprecate unused SQLite utilities in the ``scrapyd.sqlite`` module.

  - ``SqliteDict``
  - ``SqlitePickleDict``
  - ``SqlitePriorityQueue``
  - ``PickleSqlitePriorityQueue``

- Scrapy 0.x support.
- Python 2.6 support.

Fixed
~~~~~

- Poller race condition for concurrently accessed queues.

1.1.1 (2016-11-03)
------------------

Added
~~~~~

- Document and include missing configuration options in ``default_scrapyd.conf``.
- Document the spider queue's ``priority`` argument.
- Enable some missing tests for the SQLite queues.

Removed
~~~~~~~

- Disable bdist_wheel command in setup to define dynamic requirements, despite pip-7 wheel caching bug.

Fixed
~~~~~

- Use correct type adapter for sqlite3 blobs. In some systems, a wrong type adapter leads to incorrect buffer reads/writes.
- ``FEED_URI`` was always overridden by Scrapyd.
- Specify maximum versions for requirements that became incompatible.
- Mark package as zip-unsafe because Twistd requires a plain ``txapp.py``.

1.1.0 (2015-06-29)
------------------

Added
~~~~~

- Add ``node_name`` (hostname) to webservice responses. (:commit:`fac3a5c`, :commit:`4aebe1c`)
- Add ``start_time`` to the response from the :ref:`listjobs.json` webservice. (:commit:`6712af9`, :commit:`acd460b`)

Changed
~~~~~~~

- Move scrapyd-deploy command to `scrapyd-client <https://pypi.org/project/scrapyd-client/>`__ package. (:commit:`c1358dc`, :commit:`c9d66ca`, :commit:`191353e`)
- Allow remote ``items_dir`` configuration. (:commit:`e261591`, :commit:`35a21db`)
- Look for a ``~/.scrapyd.conf`` file in the user's home directory. (:commit:`1fce99b`)

Fixed
~~~~~

- Check if a spider exists before scheduling it. (:issue:`8`, :commit:`288afef`, :commit:`a185ff2`)
- Sanitize version names when creating egg paths. (:commit:`8023720`)
- Generate correct feed URIs, using w3lib. (:commit:`9a88ea5`)
- Fix git versioning for projects without annotated tags. (:issue:`34`, :commit:`e91dcf4`)
- Use valid HTML markup on website pages. (:commit:`da5664f`, :commit:`26089cd`)
- Use ``file`` protocol for ``SCRAPY_FEED_URI`` environment variable on Windows. (:commit:`4f0060a`)
- Copy ``JsonResource`` class from Scrapy, which no longer provides it. (:commit:`99ea920`)
- Lowercase ``scrapyd`` package name. (:commit:`1adfc31`).
- Mark package as zip-unsafe, because Twisted requires a plain ``txapp.py``. (:commit:`f27c054`)
- Install scripts using ``entry_points`` instead of ``scripts``. (:commit:`b670f5e`)

1.0.2 (2016-03-28)
------------------

Fixed
~~~~~

- Mark package as zip-unsafe, because Twisted requires a plain ``txapp.py``.
- Specify maximum versions for compatible requirements.

1.0.1 (2013-09-02)
------------------

*Trivial update*

1.0.0 (2013-09-02)
------------------

First standalone release (it was previously shipped with Scrapy until Scrapy 0.16).
