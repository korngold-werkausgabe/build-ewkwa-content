<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:mei="http://www.music-encoding.org/ns/mei"
  xmlns="http://www.music-encoding.org/ns/mei"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  version="1.0">

  <xsl:output indent="yes"/>
  <xsl:param name="title" select="''"/>
  <xsl:param name="sigle" select="''"/>
  <xsl:param name="manifestationFile" select="''"/>

  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="mei:fileDesc">
    <mei:fileDesc>
      <mei:titleStmt>
        <mei:title><xsl:value-of select="$title"/></mei:title>
      </mei:titleStmt>
      <editionStmt>
        <edition>
          <identifier type="siglum"><xsl:value-of select="$sigle"/></identifier>
        </edition>
        </editionStmt>
      <mei:manifestationList>
        <xsl:copy-of select="document($manifestationFile)/mei:manifestation"/>
      </mei:manifestationList>
    </mei:fileDesc>
  </xsl:template>
</xsl:stylesheet>
