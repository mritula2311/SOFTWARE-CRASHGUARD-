/* The firmware path only VERIFIES Ed25519 signatures (the vehicle holds the gateway public key); key generation and signing, which need randombytes, are not part of it. This stub makes any use a hard failure. */
#include <stdlib.h>
void randombytes(unsigned char *x, unsigned long long n)
{
    (void)x; (void)n;
    abort();
}
