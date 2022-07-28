pkgname="formie"
pkgver="1.0.1"
pkgrel=1
pkgdesc="Open source form application made with Flask + pure HTML/CSS/JS."
arch=("any")
url="https://github.com/div72/formie"
license=('AGPL')

depends=("python" "python-flask" "python-flask-sqlalchemy" "python-passlib" "python-argon2_cffi" "gunicorn")
makedepends=()

backup=("etc/formie/config.sh")

source=("https://github.com/div72/${pkgname}/archive/refs/tags/v${pkgver}.tar.gz"
        "formie.sh"
        "formie.service"
        "formie.sysusers"
        "formie.tmpfiles")
sha256sums=("dc98e41fec933fbe3125f8890258fd1252a49e544cfc78698ed3e8c158a63c3e"
            "SKIP"
            "SKIP"
            "SKIP"
            "SKIP")

build() {
  # Reserved for future use.
  true
}

package() {
    mkdir -p "${pkgdir}/opt/"
    cp -r "${srcdir}/${pkgname}-${pkgver}/" "${pkgdir}/opt/"
    mv "${pkgdir}/opt/${pkgname}-${pkgver}" "${pkgdir}/opt/${pkgname}"
    chmod -R 755 "${pkgdir}/opt/${pkgname}/"
    install -Dm755 "${srcdir}/${pkgname}.sh" "${pkgdir}/usr/bin/${pkgname}"
    install -Dm770 "${srcdir}/${pkgname}-${pkgver}/config-example.sh" "${pkgdir}/etc/${pkgname}/config.sh"
    install -Dm644 "${srcdir}/${pkgname}.service" "${pkgdir}/usr/lib/systemd/system/${pkgname}.service"
    install -Dm644 "${srcdir}/${pkgname}.sysusers" "${pkgdir}/usr/lib/sysusers.d/${pkgname}.conf"
    install -Dm644 "${srcdir}/${pkgname}.tmpfiles" "${pkgdir}/usr/lib/tmpfiles.d/${pkgname}.conf"

    chown -R root:root "${pkgdir}"
}
